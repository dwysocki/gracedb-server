try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from django.test import override_settings

from alerts.models import Contact, Notification
from alerts.email import issue_email_alerts, prepare_email_body
from core.tests.utils import GraceDbTestBase
from core.time_utils import gpsToUtc
from events.models import Label
from superevents.tests.mixins import SupereventCreateMixin


class TestEmailBody(GraceDbTestBase, SupereventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestEmailBody, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        cls.event = cls.superevent.preferred_event

        # Create a few labels
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')

    def test_new_event(self):
        """Test email contents for vanilla new event"""
        # Get email body
        email_body = prepare_email_body(self.event, 'new')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('New {grp} / {pipeline} event: {gid}'.format(
            grp=self.event.group.name, pipeline=self.event.pipeline.name,
            gid=self.event.graceid), lines[0])
        self.assertIn('Event time (GPS): {gps}'.format(gps=self.event.gpstime),
            lines[2])
        self.assertIn('Event time (UTC): {utc}'.format(utc=gpsToUtc(
            self.event.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.event.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.event.labels.values_list('name', flat=True))),
            lines[7])

    def test_new_event_more_info(self):
        """Test email contents for more interesting new event"""
        # Make event more interesting
        self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)
        self.event.far = 1e-10
        self.event.singleinspiral_set.create(mass1=3, mass2=1)
        self.event.instruments = 'I1,I2'
        self.event.save()

        # Get email body
        email_body = prepare_email_body(self.event, 'new')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('New {grp} / {pipeline} event: {gid}'.format(
            grp=self.event.group.name, pipeline=self.event.pipeline.name,
            gid=self.event.graceid), lines[0])
        self.assertIn('Event time (GPS): {gps}'.format(gps=self.event.gpstime),
            lines[2])
        self.assertIn('Event time (UTC): {utc}'.format(utc=gpsToUtc(
            self.event.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.event.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.event.labels.values_list('name', flat=True))),
            lines[7])
        self.assertIn('Instruments: {inst}'.format(inst=
            self.event.instruments), lines[8])
        self.assertIn('Component masses: {m1}, {m2}'.format(
            m1=self.event.singleinspiral_set.first().mass1,
            m2=self.event.singleinspiral_set.first().mass2), lines[9])

    def test_update_event(self):
        """Test email contents for event update"""
        # Get email body
        email_body = prepare_email_body(self.event, 'update')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('Updated {grp} / {pipeline} event: {gid}'.format(
            grp=self.event.group.name, pipeline=self.event.pipeline.name,
            gid=self.event.graceid), lines[0])
        self.assertIn('Event time (GPS): {gps}'.format(gps=self.event.gpstime),
            lines[2])
        self.assertIn('Event time (UTC): {utc}'.format(utc=gpsToUtc(
            self.event.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.event.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.event.labels.values_list('name', flat=True))),
            lines[7])

    def test_label_added_event(self):
        """Test email contents for label_added to event alert"""
        # Get email body
        email_body = prepare_email_body(self.event, 'label_added',
            label=self.label1)

        # Check email body
        lines = email_body.split('\n')
        self.assertIn(('Label {label} added to {grp} / {pipeline} event: '
            '{gid}').format(label=self.label1.name, grp=self.event.group.name,
            pipeline=self.event.pipeline.name, gid=self.event.graceid),
            lines[0])
        self.assertIn('Event time (GPS): {gps}'.format(gps=self.event.gpstime),
            lines[2])
        self.assertIn('Event time (UTC): {utc}'.format(utc=gpsToUtc(
            self.event.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.event.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.event.labels.values_list('name', flat=True))),
            lines[7])

    def test_label_removed_event(self):
        """Test email contents for label_removed to event alert"""
        # Get email body
        email_body = prepare_email_body(self.event, 'label_removed',
            label=self.label1)

        # Check email body
        lines = email_body.split('\n')
        self.assertIn(('Label {label} removed from {grp} / {pipeline} event: '
            '{gid}').format(label=self.label1.name, grp=self.event.group.name,
            pipeline=self.event.pipeline.name, gid=self.event.graceid),
            lines[0])
        self.assertIn('Event time (GPS): {gps}'.format(gps=self.event.gpstime),
            lines[2])
        self.assertIn('Event time (UTC): {utc}'.format(utc=gpsToUtc(
            self.event.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.event.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.event.labels.values_list('name', flat=True))),
            lines[7])

    def test_new_superevent(self):
        """Test email contents for vanilla new superevent"""
        # Get email body
        email_body = prepare_email_body(self.superevent, 'new')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('New superevent: {sid}'.format(
            sid=self.superevent.superevent_id), lines[0])
        self.assertIn('Superevent time (GPS): {gps}'.format(
            gps=self.superevent.gpstime), lines[2])
        self.assertIn('Superevent time (UTC): {utc}'.format(utc=gpsToUtc(
            self.superevent.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.superevent.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.superevent.labels.values_list('name', flat=True))),
            lines[7])

    def test_new_superevent_more_info(self):
        """Test email contents for more interesting new event"""
        # Make superevent more interesting
        self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)
        self.event.far = 1e-10
        self.event.singleinspiral_set.create(mass1=3, mass2=1)
        self.event.save()

        # Get email body
        email_body = prepare_email_body(self.superevent, 'new')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('New superevent: {sid}'.format(
            sid=self.superevent.superevent_id), lines[0])
        self.assertIn('Superevent time (GPS): {gps}'.format(
            gps=self.superevent.gpstime), lines[2])
        self.assertIn('Superevent time (UTC): {utc}'.format(utc=gpsToUtc(
            self.superevent.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.superevent.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.superevent.labels.values_list('name', flat=True))),
            lines[7])
        self.assertIn('Component masses: {m1}, {m2}'.format(
            m1=self.superevent.preferred_event.singleinspiral_set.first().mass1,
            m2=self.superevent.preferred_event.singleinspiral_set.first().mass2),
            lines[8])

    def test_update_superevent(self):
        """Test email contents for superevent update"""
        # Get email body
        email_body = prepare_email_body(self.superevent, 'update')

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('Updated superevent: {sid}'.format(
            sid=self.superevent.superevent_id), lines[0])
        self.assertIn('Superevent time (GPS): {gps}'.format(
            gps=self.superevent.gpstime), lines[2])
        self.assertIn('Superevent time (UTC): {utc}'.format(utc=gpsToUtc(
            self.superevent.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.superevent.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.superevent.labels.values_list('name', flat=True))),
            lines[7])

    def test_label_added_superevent(self):
        """Test email contents for label_added to superevent alert"""
        # Get email body
        email_body = prepare_email_body(self.superevent, 'label_added',
            label=self.label1)

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('Label {label} added to superevent: {sid}'.format(
            label=self.label1.name, sid=self.superevent.superevent_id),
            lines[0])
        self.assertIn('Superevent time (GPS): {gps}'.format(
            gps=self.superevent.gpstime), lines[2])
        self.assertIn('Superevent time (UTC): {utc}'.format(utc=gpsToUtc(
            self.superevent.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.superevent.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.superevent.labels.values_list('name', flat=True))),
            lines[7])

    def test_label_removed_superevent(self):
        """Test email contents for label_removed from superevent alert"""
        # Get email body
        email_body = prepare_email_body(self.superevent, 'label_removed',
            label=self.label1)

        # Check email body
        lines = email_body.split('\n')
        self.assertIn('Label {label} removed from superevent: {sid}'.format(
            label=self.label1.name, sid=self.superevent.superevent_id),
            lines[0])
        self.assertIn('Superevent time (GPS): {gps}'.format(
            gps=self.superevent.gpstime), lines[2])
        self.assertIn('Superevent time (UTC): {utc}'.format(utc=gpsToUtc(
            self.superevent.gpstime).isoformat()), lines[3])
        self.assertIn('FAR: {far}'.format(far=self.superevent.far), lines[6])
        self.assertIn('Labels: {labels}'.format(labels=", ".join(
            self.superevent.labels.values_list('name', flat=True))),
            lines[7])


@unittest.skip('This needs to be updated for EGAD')
@mock.patch('alerts.email.EmailMessage')
class TestEmailSend(GraceDbTestBase, SupereventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestEmailSend, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        cls.event = cls.superevent.preferred_event

        # Create a few labels
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')

        # Create a few email contacts
        cls.contact1 = Contact.objects.create(user=cls.internal_user,
            description='contact1', email='contact1@test.com',
            verified=True)
        cls.contact2 = Contact.objects.create(user=cls.internal_user,
            description='contact2', email='contact2@test.com',
            verified=True)
        cls.contacts = Contact.objects.filter(pk__in=[cls.contact1.pk,
            cls.contact2.pk])

    def test_new_superevent(self, mock_email):
        """Test contacts and email subject for new superevent alert"""
        issue_email_alerts(self.superevent, 'new', self.contacts)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, '[gracedb] Superevent created: {sid}'
            .format(sid=self.superevent.superevent_id))

    def test_update_superevent(self, mock_email):
        """Test contacts and email subject for update superevent alert"""
        issue_email_alerts(self.superevent, 'update', self.contacts)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, '[gracedb] Superevent updated: {sid}'
            .format(sid=self.superevent.superevent_id))

    def test_label_added_superevent(self, mock_email):
        """Test contacts and email subject for label_added superevent alert"""
        issue_email_alerts(self.superevent, 'label_added', self.contacts,
            label=self.label1)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, ('[gracedb] Superevent labeled with '
            '{label}: {sid}').format(label=self.label1.name,
            sid=self.superevent.superevent_id))

    def test_label_removed_superevent(self, mock_email):
        """
        Test contacts and email subject for label_removed superevent alert
        """
        issue_email_alerts(self.superevent, 'label_removed', self.contacts,
            label=self.label1)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, ('[gracedb] Label {label} removed from '
            'superevent: {sid}').format(label=self.label1.name,
            sid=self.superevent.superevent_id))

    def test_new_event(self, mock_email):
        """Test contacts and email subject for new event alert"""
        issue_email_alerts(self.event, 'new', self.contacts)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, '[gracedb] {pipeline} event created: {gid}'
            .format(pipeline=self.event.pipeline.name, gid=self.event.graceid))

    def test_update_event(self, mock_email):
        """Test contacts and email subject for update event alert"""
        issue_email_alerts(self.event, 'update', self.contacts)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, '[gracedb] {pipeline} event updated: {gid}'
            .format(pipeline=self.event.pipeline.name, gid=self.event.graceid))

    def test_label_added_superevent(self, mock_email):
        """Test contacts and email subject for label_added event alert"""
        issue_email_alerts(self.event, 'label_added', self.contacts,
            label=self.label1)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, ('[gracedb] {pipeline} event labeled with '
            '{label}: {gid}').format(pipeline=self.event.pipeline.name,
            label=self.label1.name, gid=self.event.graceid))

    def test_label_removed_event(self, mock_email):
        """Test contacts and email subject for label_removed event alert"""
        issue_email_alerts(self.event, 'label_removed', self.contacts,
            label=self.label1)

        # Check calls to EmailMessage init
        self.assertEqual(mock_email.call_count, self.contacts.count())

        # Check 'to' address
        tos = [ca[1]['to'][0] for ca in mock_email.call_args_list]
        self.assertEqual(sorted(tos), sorted(list(self.contacts.values_list(
            'email', flat=True))))

        # Check subject
        subject = mock_email.call_args[1]['subject']
        self.assertEqual(subject, ('[gracedb] Label {label} removed from '
            '{pipeline} event: {gid}').format(label=self.label1.name,
            pipeline=self.event.pipeline.name, gid=self.event.graceid))
