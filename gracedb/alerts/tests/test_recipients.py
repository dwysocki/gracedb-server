import mock

from django.test import override_settings

from alerts.issuers.events import EventAlertIssuer, EventLabelAlertIssuer
from alerts.issuers.superevents import (
    SupereventAlertIssuer, SupereventLabelAlertIssuer,
)
from alerts.models import Contact, Notification
from core.tests.utils import GraceDbTestBase
from events.models import Label, Group, Pipeline, Search
from events.tests.mixins import EventCreateMixin
from superevents.tests.mixins import SupereventCreateMixin


@override_settings(
    SEND_XMPP_ALERTS=False,
    SEND_EMAIL_ALERTS=True,
    SEND_PHONE_ALERTS=True,
)
@mock.patch('alerts.main.issue_phone_alerts')
@mock.patch('alerts.main.issue_email_alerts')
class TestEventRecipients(GraceDbTestBase, EventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestEventRecipients, cls).setUpTestData()

        # Create an event
        cls.event = cls.create_event('fake_group', 'fake_pipeline',
            'fake_search', user=cls.internal_user)

        # Create a bunch of notifications
        cls.far_thresh = 0.01
        cls.notification_dict = {}
        cls.notification_dict['basic'] = Notification.objects.create(
            user=cls.internal_user, description='basic',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far'] = Notification.objects.create(
            user=cls.internal_user, description='far',
            far_threshold=cls.far_thresh,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['nscand'] = Notification.objects.create(
            user=cls.internal_user, description='nscand',
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far_nscand'] = Notification.objects.create(
            user=cls.internal_user, description='far_nscand',
            far_threshold=cls.far_thresh, ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['labels'] = Notification.objects.create(
            user=cls.internal_user, description='labels',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far_labels'] = Notification.objects.create(
            user=cls.internal_user, description='far_labels',
            far_threshold=cls.far_thresh,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['nscand_labels'] = Notification.objects.create(
            user=cls.internal_user, description='nscand_labels',
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far_nscand_labels'] = \
            Notification.objects.create(user=cls.internal_user,
            description='far_nscand_labels', far_threshold=cls.far_thresh,
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['labelq'] = Notification.objects.create(
            label_query='TEST_LABEL3 & ~TEST_LABEL4',
            user=cls.internal_user, description='labelq',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far_labelq'] = Notification.objects.create(
            user=cls.internal_user, description='far_labelq',
            far_threshold=cls.far_thresh,
            label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['nscand_labelq'] = Notification.objects.create(
            user=cls.internal_user, description='nscand_labelq',
            ns_candidate=True, label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['far_nscand_labelq'] = \
            Notification.objects.create(user=cls.internal_user,
            description='far_nscand_labelq', far_threshold=cls.far_thresh,
            ns_candidate=True, label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)

        # Group-pipeline-search notification
        group, _ = Group.objects.get_or_create(name='TEST_GROUP')
        pipeline, _ = Pipeline.objects.get_or_create(name='TEST_PIPELINE')
        search, _ = Search.objects.get_or_create(name='TEST_SEARCH')
        cls.notification_dict['gps'] = Notification.objects.create(
            user=cls.internal_user, description='gps',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.notification_dict['gps'].groups.add(group)
        cls.notification_dict['gps'].pipelines.add(pipeline)
        cls.notification_dict['gps'].searches.add(search)

        # Add label stuff
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')
        cls.label3, _ = Label.objects.get_or_create(name='TEST_LABEL3')
        cls.label4, _ = Label.objects.get_or_create(name='TEST_LABEL4')
        for k in cls.notification_dict:
            if 'labels' in k:
                cls.notification_dict[k].labels.add(cls.label1)
                cls.notification_dict[k].labels.add(cls.label2)
            elif 'labelq' in k:
                cls.notification_dict[k].labels.add(cls.label3)
                cls.notification_dict[k].labels.add(cls.label4)

        # Create an email and phone contact for each notification
        for k in cls.notification_dict:
            n = cls.notification_dict[k]
            n.contacts.create(user=cls.internal_user,
                description=n.description, email='test@test.com',
                verified=True)
            n.contacts.create(user=cls.internal_user,
                description=n.description, phone='12345678901',
                phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

    def test_new(self, email_mock, phone_mock):
        """Test alerts for event creation - no FAR, no NSCAND"""
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Should just be the "basic" notification being triggered
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic')
        self.assertEqual(phone_recips.first().description, 'basic')

    def test_new_with_far(self, email_mock, phone_mock):
        """Test alerts for event creation with FAR"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n.contacts.create(user=self.internal_user,
            description=n.description, email='test@test.com',
            verified=True)
        n.contacts.create(user=self.internal_user,
            description=n.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic and FAR alerts should be triggered, but not the "new" FAR
        # one we defined with a really low threshold
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['basic', 'far'])

        # Ensure that "new" FAR alert is not in the lists
        self.assertFalse(email_recips.filter(
            description=n.description).exists())
        self.assertFalse(phone_recips.filter(
            description=n.description).exists())


    def test_new_with_nscand(self, email_mock, phone_mock):
        """Test alerts for event creation with NS candidate"""
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only basic and NSCAND alerts should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['basic', 'nscand'])

    def test_new_with_far_nscand(self, email_mock, phone_mock):
        """Test alerts for event creation with FAR and NS candidate"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Create a new notification with too low of a FAR threshold
        n = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n.contacts.create(user=self.internal_user,
            description=n.description, email='test@test.com',
            verified=True)
        n.contacts.create(user=self.internal_user,
            description=n.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic and FAR alerts should be triggered, but not the "new" FAR
        # one we defined with a really low threshold
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description,
                    ['basic', 'far', 'nscand', 'far_nscand'])

        # Ensure that "new" FAR alert is not in the lists
        self.assertFalse(email_recips.filter(
            description=n.description).exists())
        self.assertFalse(phone_recips.filter(
            description=n.description).exists())

    def test_new_with_group_pipeline_search(self, email_mock, phone_mock):
        """Test alerts for event creation which match group-pipeline-search"""
        # Change event group, pipeline, search
        self.event.group = self.notification_dict['gps'].groups.first()
        self.event.pipeline = self.notification_dict['gps'].pipelines.first()
        self.event.search = self.notification_dict['gps'].searches.first()

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic alert and 'gps' alert (which matches group-pipeline-search)
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['basic', 'gps'])

    def test_update_with_no_change(self, email_mock, phone_mock):
        """Test alerts for event update with no FAR or NSCAND change"""
        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_same_far(self, email_mock, phone_mock):
        """Test alerts for event update with no FAR or NSCAND change"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.event.far)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_lower_far(self, email_mock, phone_mock):
        """Test alerts for event update with lower FAR"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert should be triggered and not the
        # n_low or n_high that we defined here
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'far')
        self.assertEqual(phone_recips.first().description, 'far')

    def test_update_with_nscand(self, email_mock, phone_mock):
        """Test alerts for event update with NSCAND trigger"""
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_nscand=False)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'nscand' alert should be triggered
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'nscand')
        self.assertEqual(phone_recips.first().description, 'nscand')

    def test_update_with_far_no_prev_far(self, email_mock, phone_mock):
        """Test alerts for event update with new FAR, no previous FAR"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=None)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert and 'far_high' should be in here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_high'])

    def test_update_with_far_no_old_far_passed(self, email_mock,
        phone_mock):
        """Test alerts for event update with new FAR, no old FAR passed"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert and 'far_high' should be in here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_high'])

    def test_update_with_nscand_still_true(self, email_mock, phone_mock):
        """Test alerts for event update where NSCAND was and is true"""
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_nscand=True)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_lower_far_nscand(self, email_mock, phone_mock):
        """Test alerts for event update with lower FAR and NSCAND"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2, old_nscand=False)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert should be triggered and not the
        # n_low or n_high that we defined here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 3)
            for r in recips:
                self.assertIn(r.description, ['far', 'nscand', 'far_nscand'])

    def test_labeled_update_with_lower_far(self, email_mock, phone_mock):
        """
        Test alerts for an event which has labels and updated with lower FAR
        """
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Add label1 to event - not enough to match labels yet
        self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['far'])

        # Add label2 to event - should match now
        self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements and 'far_labels' should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_labels'])

    def test_labelq_update_with_lower_far(self, email_mock, phone_mock):
        """Test alerts for event update with lower FAR and label_query match"""
        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Add labels to event - this set of labels shouldn't match label query
        self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['far'])

        # Remove label4 and the label query should match
        self.event.labelling_set.get(label=self.label4).delete()

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        # 'far_labelq' (with label query) should now be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_labelq'])

    def test_update_match_group_pipeline_search(self, email_mock, phone_mock):
        """Test alerts for event update which match group-pipeline-search"""
        # Change event group, pipeline, search
        self.event.group = self.notification_dict['gps'].groups.first()
        self.event.pipeline = self.notification_dict['gps'].pipelines.first()
        self.event.search = self.notification_dict['gps'].searches.first()

        # Change GPS notification to have a far_threshold
        self.notification_dict['gps'].far_threshold = self.far_thresh

        # Add FAR to event
        self.event.far = 1e-10
        self.event.save()

        # Issue alerts
        EventAlertIssuer(self.event, alert_type='update').issue_alerts(
            old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_gps'])

    def test_label_added(self, email_mock, phone_mock):
        """Test adding label alert for event"""
        # Add label1 to event - this shouldn't match any queries
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab1, alert_type='label_added').issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Add label2 to event
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labels' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

        # Issue alert for label 1 now that it has both labels; should be
        # the same result
        EventLabelAlertIssuer(lab1, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labels' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

    def test_label_added_extra_labels(self, email_mock, phone_mock):
        """Test adding label alert for event with other labels"""
        # Add label 1, 2, and 4 to event
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts for label 2
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # The 'labels' trigger only requires label1 and label2, but it should
        # still trigger on label2 addition even though label4 is also present
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

    def test_label_added_with_far(self, email_mock, phone_mock):
        """Test adding label alert for event with FAR"""
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add label1 and label2 to event
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and labels w/ FAR ('far_labels') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labels', 'far_labels'])

    def test_label_added_with_nscand(self, email_mock, phone_mock):
        """Test adding label alert for event with NSCAND"""
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label1 and label2 to event
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and labels w/ NSCAND ('nscand_labels') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labels', 'nscand_labels'])

    def test_label_added_with_far_nscand(self, email_mock, phone_mock):
        """Test adding label alert for event with FAR threshold and NSCAND"""
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label1 and label2 to event
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger, labels with FAR, labels with NSCAND, and
        # labels with FAR and NSCAND should all be triggered
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labels', 'far_labels',
                    'nscand_labels', 'far_nscand_labels'])

    def test_label_added_with_gps(self, email_mock, phone_mock):
        """
        Test adding label alert for event with group-pipeline-search
        requirements
        """
        # Change event group, pipeline, search
        self.event.group = self.notification_dict['gps'].groups.first()
        self.event.pipeline = self.notification_dict['gps'].pipelines.first()
        self.event.search = self.notification_dict['gps'].searches.first()

        # Add label 1 and 2 to notification
        self.notification_dict['gps'].labels.add(self.label1)
        self.notification_dict['gps'].labels.add(self.label2)

        # Add label 1 and 2 to event
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab2, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and 'gps' trigger should match
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labels', 'gps'])

    def test_label_added_labelq(self, email_mock, phone_mock):
        """Test adding label alert for event with label query match"""
        # Add label3 and label4 to event
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab4, alert_type='label_added').issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Remove label4 and the label query should match
        self.event.labelling_set.get(label=self.label4).delete()

        # Issue alerts
        EventLabelAlertIssuer(lab3, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic label_query trigger should be only match
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labelq'])

    def test_label_added_labelq_with_far(self, email_mock, phone_mock):
        """Test adding label alert for event with FAR and label query match"""
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add label3 to event
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab3, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger and label query w/ FAR ('far_labelq') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq'])

    def test_label_added_labelq_with_nscand(self, email_mock, phone_mock):
        """
        Test adding label alert for event with NSCAND and label query match
        """
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label3 to event
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab3, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger and label query w/ NSCAND ('nscand_labelq')
        # trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'nscand_labelq'])

    def test_label_added_labelq_with_far_nscand(self, email_mock, phone_mock):
        """
        Test adding label alert for event with FAR threshold and NSCAND and
        label query match
        """
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label3 to event
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab3, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger, label query with FAR, label query with
        # NSCAND, and label query with FAR and NSCAND should all be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq',
                    'nscand_labelq', 'far_nscand_labelq'])

    def test_label_added_labelq_with_gps(self, email_mock, phone_mock):
        """
        Test adding label alert for event with group-pipeline-search
        requirements and label query match
        """
        # Change event group, pipeline, search
        self.event.group = self.notification_dict['gps'].groups.first()
        self.event.pipeline = self.notification_dict['gps'].pipelines.first()
        self.event.search = self.notification_dict['gps'].searches.first()

        # Add label query to notification
        self.notification_dict['gps'].label_query = '{l3} & ~{l4}'.format(
            l3=self.label3.name, l4=self.label4.name)
        self.notification_dict['gps'].labels.add(self.label3)
        self.notification_dict['gps'].labels.add(self.label4)
        self.notification_dict['gps'].save()

        # Add label3 to event 
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab3, alert_type='label_added').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger and 'gps' trigger should match
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'gps'])

    def test_label_removed_match_labels(self, email_mock, phone_mock):
        """
        Test label_removed alert for event where only triggers with
        labels, not label queries are matched
        """
        # Add labels 1 and 2
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Remove label 2 and issue alert for label 2 removal
        self.event.labelling_set.get(label=self.label2).delete()
        EventLabelAlertIssuer(lab2, alert_type='label_removed').issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Add labels 2 and 3
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Remove label 3 and issue alert
        self.event.labelling_set.get(label=self.label3).delete()
        EventLabelAlertIssuer(lab3, alert_type='label_removed').issue_alerts()

        # Although the event has label1 and label2 and matches the
        # 'labels' trigger, this trigger was matched last time either
        # label1 or label2 was added, and label3 being removed doesn't
        # change that (i.e., label_removed alerts only trigger notifications
        # with label queries)
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_label_removed(self, email_mock, phone_mock):
        """Test label_removed alert for event with label query match"""
        # Add labels 3 and 4
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.event.labelling_set.get(label=self.label4).delete()
        EventLabelAlertIssuer(lab4, alert_type='label_removed').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labelq' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labelq'])

    def test_label_removed_with_far(self, email_mock, phone_mock):
        """
        Test label_removed alert for event with label query match and
        FAR threshold match"""
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add labels 3 and 4
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.event.labelling_set.get(label=self.label4).delete()
        EventLabelAlertIssuer(lab4, alert_type='label_removed').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labelq' and label_query with FAR should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq'])

    def test_label_removed_with_nscand(self, email_mock, phone_mock):
        """Test label_removed alert with label query match and NSCAND match"""
        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add labels 3 and 4
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.event.labelling_set.get(label=self.label4).delete()
        EventLabelAlertIssuer(lab4, alert_type='label_removed').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic label query trigger and label query w/ NSCAND should be
        # triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'nscand_labelq'])

    def test_label_removed_with_far_nscand(self, email_mock, phone_mock):
        """
        Test label_removed alert for event with FAR threshold and NSCAND
        and label query match
        """
        # Set event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add labels 3 and 4
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.event.labelling_set.get(label=self.label4).delete()
        EventLabelAlertIssuer(lab4, alert_type='label_removed').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Should match basic label query trigger, label query with FAR,
        # label query with NSCAND, and label query with FAR and NSCAND
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq',
                    'nscand_labelq', 'far_nscand_labelq'])

    def test_label_removed_with_gps(self, email_mock, phone_mock):
        """
        Test label_removed alert for event with group-pipeline-search
        requirements and label query match
        """
        # Change event group, pipeline, search
        self.event.group = self.notification_dict['gps'].groups.first()
        self.event.pipeline = self.notification_dict['gps'].pipelines.first()
        self.event.search = self.notification_dict['gps'].searches.first()

        # Add labels 3 and 4
        lab3 = self.event.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.event.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Add label query to 'gps' trigger
        self.notification_dict['gps'].label_query = '{l3} & ~{l4}'.format(
            l3=self.label3.name, l4=self.label4.name)
        self.notification_dict['gps'].labels.add(self.label3)
        self.notification_dict['gps'].labels.add(self.label4)
        self.notification_dict['gps'].save()

        # Remove label 4 and issue alert for label 4 removal
        self.event.labelling_set.get(label=self.label4).delete()
        EventLabelAlertIssuer(lab4, alert_type='label_removed').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and 'gps' trigger should match
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'gps'])


@override_settings(
    SEND_XMPP_ALERTS=False,
    SEND_EMAIL_ALERTS=True,
    SEND_PHONE_ALERTS=True,
)
@mock.patch('alerts.main.issue_phone_alerts')
@mock.patch('alerts.main.issue_email_alerts')
class TestSupereventRecipients(GraceDbTestBase, SupereventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventRecipients, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        # preferred event
        cls.event = cls.superevent.preferred_event

        # Create a bunch of notifications
        cls.far_thresh = 0.01
        cls.notification_dict = {}
        cls.notification_dict['basic'] = Notification.objects.create(
            user=cls.internal_user, description='basic',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far'] = Notification.objects.create(
            user=cls.internal_user, description='far',
            far_threshold=cls.far_thresh,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['nscand'] = Notification.objects.create(
            user=cls.internal_user, description='nscand',
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far_nscand'] = Notification.objects.create(
            user=cls.internal_user, description='far_nscand',
            far_threshold=cls.far_thresh, ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['labels'] = Notification.objects.create(
            user=cls.internal_user, description='labels',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far_labels'] = Notification.objects.create(
            user=cls.internal_user, description='far_labels',
            far_threshold=cls.far_thresh,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['nscand_labels'] = Notification.objects.create(
            user=cls.internal_user, description='nscand_labels',
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far_nscand_labels'] = \
            Notification.objects.create(user=cls.internal_user,
            description='far_nscand_labels', far_threshold=cls.far_thresh,
            ns_candidate=True,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['labelq'] = Notification.objects.create(
            label_query='TEST_LABEL3 & ~TEST_LABEL4',
            user=cls.internal_user, description='labelq',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far_labelq'] = Notification.objects.create(
            user=cls.internal_user, description='far_labelq',
            far_threshold=cls.far_thresh,
            label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['nscand_labelq'] = Notification.objects.create(
            user=cls.internal_user, description='nscand_labelq',
            ns_candidate=True, label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.notification_dict['far_nscand_labelq'] = \
            Notification.objects.create(user=cls.internal_user,
            description='far_nscand_labelq', far_threshold=cls.far_thresh,
            ns_candidate=True, label_query='TEST_LABEL3 & ~TEST_LABEL4',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)

        # Add label stuff
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')
        cls.label3, _ = Label.objects.get_or_create(name='TEST_LABEL3')
        cls.label4, _ = Label.objects.get_or_create(name='TEST_LABEL4')
        for k in cls.notification_dict:
            if 'labels' in k:
                cls.notification_dict[k].labels.add(cls.label1)
                cls.notification_dict[k].labels.add(cls.label2)
            elif 'labelq' in k:
                cls.notification_dict[k].labels.add(cls.label3)
                cls.notification_dict[k].labels.add(cls.label4)

        # Create an email and phone contact for each notification
        for k in cls.notification_dict:
            n = cls.notification_dict[k]
            n.contacts.create(user=cls.internal_user,
                description=n.description, email='test@test.com',
                verified=True)
            n.contacts.create(user=cls.internal_user,
                description=n.description, phone='12345678901',
                phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

    def test_new(self, email_mock, phone_mock):
        """Test alerts for superevent creation - no FAR, no NSCAND"""
        SupereventAlertIssuer(self.superevent, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Should just be the "basic" notification being triggered
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic')
        self.assertEqual(phone_recips.first().description, 'basic')

    def test_new_with_far(self, email_mock, phone_mock):
        """Test alerts for superevent creation with FAR"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n.contacts.create(user=self.internal_user,
            description=n.description, email='test@test.com',
            verified=True)
        n.contacts.create(user=self.internal_user,
            description=n.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic and FAR alerts should be triggered, but not the "new" FAR
        # one we defined with a really low threshold
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['basic', 'far'])

        # Ensure that "new" FAR alert is not in the lists
        self.assertFalse(email_recips.filter(
            description=n.description).exists())
        self.assertFalse(phone_recips.filter(
            description=n.description).exists())

    def test_new_with_nscand(self, email_mock, phone_mock):
        """Test alerts for superevent creation with NS candidate"""
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only basic and NSCAND alerts should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['basic', 'nscand'])

    def test_new_with_far_nscand(self, email_mock, phone_mock):
        """Test alerts for superevent creation with FAR and NS candidate"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Create a new notification with too low of a FAR threshold
        n = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n.contacts.create(user=self.internal_user,
            description=n.description, email='test@test.com',
            verified=True)
        n.contacts.create(user=self.internal_user,
            description=n.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='new').issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic and FAR alerts should be triggered, but not the "new" FAR
        # one we defined with a really low threshold
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description,
                    ['basic', 'far', 'nscand', 'far_nscand'])

        # Ensure that "new" FAR alert is not in the lists
        self.assertFalse(email_recips.filter(
            description=n.description).exists())
        self.assertFalse(phone_recips.filter(
            description=n.description).exists())

    def test_update_with_no_change(self, email_mock, phone_mock):
        """Test alerts for superevent update with no FAR or NSCAND change"""
        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_same_far(self, email_mock, phone_mock):
        """Test alerts for superevent update with no FAR or NSCAND change"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.event.far)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_lower_far(self, email_mock, phone_mock):
        """Test alerts for superevent update with lower FAR"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert should be triggered and not the
        # n_low or n_high that we defined here
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'far')
        self.assertEqual(phone_recips.first().description, 'far')

    def test_update_with_new_preferred_event_no_far(self, email_mock,
        phone_mock):
        """
        Test alerts for superevent update with new preferred_event with
        no FAR
        """
        # Update preferred event
        ev = self.create_event('fake_group', 'fake_pipeline',
            'fake_search', user=self.internal_user)
        self.superevent.preferred_event = ev

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.event.far)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_new_preferred_event_same_far(self, email_mock,
        phone_mock):
        """
        Test alerts for superevent update with new preferred_event with
        same FAR
        """
        # Update preferred event
        ev = self.create_event('fake_group', 'fake_pipeline',
            'fake_search', user=self.internal_user)
        ev.far = 1e-10
        ev.save()
        self.superevent.preferred_event = ev

        # Add FAR to old preferred event
        self.event.far = 1e-10
        self.event.save()

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.event.far)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_nscand(self, email_mock, phone_mock):
        """Test alerts for superevent update with NSCAND trigger"""
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_nscand=False)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'nscand' alert should be triggered
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(phone_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'nscand')
        self.assertEqual(phone_recips.first().description, 'nscand')

    def test_update_with_far_no_prev_far(self, email_mock, phone_mock):
        """Test alerts for superevent update with new FAR, no previous FAR"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=None)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert and 'far_high' should be in here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_high'])

    def test_update_with_far_no_old_far_passed(self, email_mock,
        phone_mock):
        """Test alerts for superevent update with new FAR, no old FAR passed"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert and 'far_high' should be in here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_high'])

    def test_update_with_nscand_still_true(self, email_mock, phone_mock):
        """Test alerts for superevent update where NSCAND was and is true"""
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_nscand=True)

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_update_with_lower_far_nscand(self, email_mock, phone_mock):
        """Test alerts for superevent update with lower FAR and NSCAND"""
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Create a new notification with too low of a FAR threshold
        n_low = Notification.objects.create(user=self.internal_user,
            description='far_low', far_threshold=1e-20,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, email='test@test.com',
            verified=True)
        n_low.contacts.create(user=self.internal_user,
            description=n_low.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Create a new notification with too high of a FAR threshold
        n_high = Notification.objects.create(user=self.internal_user,
            description='far_high', far_threshold=1,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, email='test@test.com',
            verified=True)
        n_high.contacts.create(user=self.internal_user,
            description=n_high.description, phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=True)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2, old_nscand=False)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only the original 'far' alert should be triggered and not the
        # n_low or n_high that we defined here
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 3)
            for r in recips:
                self.assertIn(r.description, ['far', 'nscand', 'far_nscand'])

    def test_labeled_update_with_lower_far(self, email_mock, phone_mock):
        """
        Test alerts for a superevent which has labels and updated with lower
        FAR
        """
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Add label1 to superevent - not enough to match labels yet
        self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['far'])

        # Add label2 to event - should match now
        self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements and 'far_labels' should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_labels'])

    def test_labelq_update_with_lower_far(self, email_mock, phone_mock):
        """
        Test alerts for superevent update with lower FAR and label_query
        match
        """
        # Add FAR to preferred event
        self.event.far = 1e-10
        self.event.save()

        # Add labels to superevent - this set of labels shouldn't match label
        # query
        self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['far'])

        # Remove label4 and the label query should match
        self.superevent.labelling_set.get(label=self.label4).delete()

        # Issue alerts
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=self.far_thresh*2)

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # 'far' with no label requirements should be triggered
        # 'far_labelq' (with label query) should now be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['far', 'far_labelq'])

    def test_label_added(self, email_mock, phone_mock):
        """Test adding label alert for superevent"""
        # Add label1 to superevent - this shouldn't match any queries
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab1, alert_type='label_added') \
            .issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Add label2 to superevent
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab2, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labels' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

        # Issue alert for label 1 now that it has both labels; should be
        # the same result
        SupereventLabelAlertIssuer(lab1, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labels' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

    def test_label_added_extra_labels(self, email_mock, phone_mock):
        """Test adding label alert for superevent with other labels"""
        # Add label 1, 2, and 4 to superevent
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts for label 2
        SupereventLabelAlertIssuer(lab2, alert_type='label_added')\
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # The 'labels' trigger only requires label1 and label2, but it should
        # still trigger on label2 addition even though label4 is also present
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labels'])

    def test_label_added_with_far(self, email_mock, phone_mock):
        """Test adding label alert for superevent with FAR"""
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add label1 and label2 to superevent
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab2, alert_type='label_added')\
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and labels w/ FAR ('far_labels') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labels', 'far_labels'])

    def test_label_added_with_nscand(self, email_mock, phone_mock):
        """Test adding label alert for superevent with NSCAND"""
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label1 and label2 to event
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab2, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger and labels w/ NSCAND ('nscand_labels') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labels', 'nscand_labels'])

    def test_label_added_with_far_nscand(self, email_mock, phone_mock):
        """
        Test adding label alert for superevent with FAR threshold and NSCAND
        """
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label1 and label2 to superevent
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab2, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labels' trigger, labels with FAR, labels with NSCAND, and
        # labels with FAR and NSCAND should all be triggered
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labels', 'far_labels',
                    'nscand_labels', 'far_nscand_labels'])

    def test_label_added_labelq(self, email_mock, phone_mock):
        """Test adding label alert for superevent with label query match"""
        # Add label3 and label4 to superevent
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab4, alert_type='label_added') \
            .issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Remove label4 and the label query should match
        self.superevent.labelling_set.get(label=self.label4).delete()

        # Issue alerts
        SupereventLabelAlertIssuer(lab3, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic label_query trigger should be only match
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labelq'])

    def test_label_added_labelq_with_far(self, email_mock, phone_mock):
        """
        Test adding label alert for superevent with FAR and label query match
        """
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add label3 to superevent
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab3, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger and label query w/ FAR ('far_labelq') trigger
        # should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq'])

    def test_label_added_labelq_with_nscand(self, email_mock, phone_mock):
        """
        Test adding label alert for superevent with NSCAND and label query
        match
        """
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label3 to superevent
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab3, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger and label query w/ NSCAND ('nscand_labelq')
        # trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'nscand_labelq'])

    def test_label_added_labelq_with_far_nscand(self, email_mock, phone_mock):
        """
        Test adding label alert for superevent with FAR threshold and NSCAND
        and label query match
        """
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add label3 to superevent
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab3, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic 'labelq' trigger, label query with FAR, label query with
        # NSCAND, and label query with FAR and NSCAND should all be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq',
                    'nscand_labelq', 'far_nscand_labelq'])

    def test_label_removed_match_labels(self, email_mock, phone_mock):
        """
        Test label_removed alert for superevent where only triggers with
        labels, not label queries are matched
        """
        # Add labels 1 and 2
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Remove label 2 and issue alert for label 2 removal
        self.superevent.labelling_set.get(label=self.label2).delete()
        SupereventLabelAlertIssuer(lab2, alert_type='label_removed') \
            .issue_alerts()

        # In this case, no recipients should match so the alert functions
        # are not even called
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

        # Add labels 2 and 3
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)

        # Remove label 3 and issue alert
        self.superevent.labelling_set.get(label=self.label3).delete()
        SupereventLabelAlertIssuer(lab3, alert_type='label_removed') \
            .issue_alerts()

        # Although the event has label1 and label2 and matches the
        # 'labels' trigger, this trigger was matched last time either
        # label1 or label2 was added, and label3 being removed doesn't
        # change that (i.e., label_removed alerts only trigger notifications
        # with label queries)
        email_mock.assert_not_called()
        phone_mock.assert_not_called()

    def test_label_removed(self, email_mock, phone_mock):
        """Test label_removed alert for superevent with label query match"""
        # Add labels 3 and 4
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.superevent.labelling_set.get(label=self.label4).delete()
        SupereventLabelAlertIssuer(lab4, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labelq' trigger should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 1)
            for r in recips:
                self.assertIn(r.description, ['labelq'])

    def test_label_removed_with_far(self, email_mock, phone_mock):
        """
        Test label_removed alert for superevent with label query match and
        FAR threshold match"""
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add labels 3 and 4
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.superevent.labelling_set.get(label=self.label4).delete()
        SupereventLabelAlertIssuer(lab4, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Only 'labelq' and label_query with FAR should be triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq'])

    def test_label_removed_with_nscand(self, email_mock, phone_mock):
        """Test label_removed alert with label query match and NSCAND match"""
        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add labels 3 and 4
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.superevent.labelling_set.get(label=self.label4).delete()
        SupereventLabelAlertIssuer(lab4, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Basic label query trigger and label query w/ NSCAND should be
        # triggered
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 2)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'nscand_labelq'])

    def test_label_removed_with_far_nscand(self, email_mock, phone_mock):
        """
        Test label_removed alert for superevent with FAR threshold and NSCAND
        and label query match
        """
        # Set preferred event FAR
        self.event.far = 1e-10
        self.event.save()

        # Add NSCAND to preferred event
        self.event.singleinspiral_set.create(mass1=3, mass2=1)

        # Add labels 3 and 4
        lab3 = self.superevent.labelling_set.create(label=self.label3,
            creator=self.internal_user)
        lab4 = self.superevent.labelling_set.create(label=self.label4,
            creator=self.internal_user)

        # Remove label 4 and issue alert for label 4 removal
        self.superevent.labelling_set.get(label=self.label4).delete()
        SupereventLabelAlertIssuer(lab4, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to alert functions
        email_recips = email_mock.call_args[0][2]
        phone_recips = phone_mock.call_args[0][2]

        # Should match basic label query trigger, label query with FAR,
        # label query with NSCAND, and label query with FAR and NSCAND
        for recips in [email_recips, phone_recips]:
            self.assertEqual(recips.count(), 4)
            for r in recips:
                self.assertIn(r.description, ['labelq', 'far_labelq',
                    'nscand_labelq', 'far_nscand_labelq'])


@override_settings(
    SEND_XMPP_ALERTS=False,
    SEND_EMAIL_ALERTS=True,
    SEND_PHONE_ALERTS=True,
)
@mock.patch('alerts.main.issue_phone_alerts')
@mock.patch('alerts.main.issue_email_alerts')
class TestSupereventUnverifiedRecipients(GraceDbTestBase, SupereventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventUnverifiedRecipients, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        # preferred event
        cls.event = cls.superevent.preferred_event
        # Set FAR
        cls.event.far = 1e-6

        # Create labaels
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')

        # Create a basic notification and a label query notification
        cls.notification = Notification.objects.create(
            user=cls.internal_user, description='basic', far_threshold=0.01,
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.label_notification = Notification.objects.create(
            user=cls.internal_user, description='labels',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        cls.label_notification.labels.add(cls.label1)
        cls.label_notification.labels.add(cls.label2)
        cls.label_notification.label_query = '{l1} & ~{l2}'.format(
            l1=cls.label1.name, l2=cls.label2.name)
        cls.label_notification.save()

        # Create an email and phone contact for notification
        cls.notification.contacts.create(user=cls.internal_user,
            description='basic email', email='test@test.com',
            verified=True)
        cls.notification.contacts.create(user=cls.internal_user,
            description='basic phone', phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=False)

        # Create contacts for label_query notification
        cls.label_notification.contacts.create(user=cls.internal_user,
            description='label email', email='test@test.com',
            verified=True)
        cls.label_notification.contacts.create(user=cls.internal_user,
            description='label phone', phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=False)

    def test_new_superevent(self, email_mock, phone_mock):
        """Test verified recipients for new superevent alert"""
        SupereventAlertIssuer(self.superevent, alert_type='new').issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_update_superevent(self, email_mock, phone_mock):
        """Test verified recipients for update superevent alert"""
        SupereventAlertIssuer(self.superevent, alert_type='update') \
            .issue_alerts(old_far=0.02)

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_label_added_superevent(self, email_mock, phone_mock):
        """Test verified recipients for label_added superevent alert"""
        # Add label
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        SupereventLabelAlertIssuer(lab1, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'label email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_label_removed_superevent(self, email_mock, phone_mock):
        """Test verified recipients for label_removed superevent alert"""
        # Add labels
        lab1 = self.superevent.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.superevent.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Remove label 2 and issue alerts
        lab2.delete()
        SupereventLabelAlertIssuer(lab2, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'label email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()


@override_settings(
    SEND_XMPP_ALERTS=False,
    SEND_EMAIL_ALERTS=True,
    SEND_PHONE_ALERTS=True,
)
@mock.patch('alerts.main.issue_phone_alerts')
@mock.patch('alerts.main.issue_email_alerts')
class TestEventUnverifiedRecipients(GraceDbTestBase, EventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestEventUnverifiedRecipients, cls).setUpTestData()

        # Create an event
        cls.event = cls.create_event('fake_group', 'fake_pipeline', 
            search_name='fake_search', user=cls.internal_user)
        # Set FAR
        cls.event.far = 1e-6

        # Create labaels
        cls.label1, _ = Label.objects.get_or_create(name='TEST_LABEL1')
        cls.label2, _ = Label.objects.get_or_create(name='TEST_LABEL2')

        # Create a basic notification and a label query notification
        cls.notification = Notification.objects.create(
            user=cls.internal_user, description='basic', far_threshold=0.01,
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.label_notification = Notification.objects.create(
            user=cls.internal_user, description='labels',
            category=Notification.NOTIFICATION_CATEGORY_EVENT)
        cls.label_notification.labels.add(cls.label1)
        cls.label_notification.labels.add(cls.label2)
        cls.label_notification.label_query = '{l1} & ~{l2}'.format(
            l1=cls.label1.name, l2=cls.label2.name)
        cls.label_notification.save()

        # Create an email and phone contact for notification
        cls.notification.contacts.create(user=cls.internal_user,
            description='basic email', email='test@test.com',
            verified=True)
        cls.notification.contacts.create(user=cls.internal_user,
            description='basic phone', phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=False)

        # Create contacts for label_query notification
        cls.label_notification.contacts.create(user=cls.internal_user,
            description='label email', email='test@test.com',
            verified=True)
        cls.label_notification.contacts.create(user=cls.internal_user,
            description='label phone', phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH, verified=False)

    def test_new_event(self, email_mock, phone_mock):
        """Test verified recipients for new event alert"""
        EventAlertIssuer(self.event, alert_type='new').issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_update_event(self, email_mock, phone_mock):
        """Test verified recipients for update event alert"""
        EventAlertIssuer(self.event, alert_type='update') \
            .issue_alerts(old_far=0.02)

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'basic email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_label_added_event(self, email_mock, phone_mock):
        """Test verified recipients for label_added event alert"""
        # Add label
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)

        # Issue alerts
        EventLabelAlertIssuer(lab1, alert_type='label_added') \
            .issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'label email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()

    def test_label_removed_event(self, email_mock, phone_mock):
        """Test verified recipients for label_removed event alert"""
        # Add labels
        lab1 = self.event.labelling_set.create(label=self.label1,
            creator=self.internal_user)
        lab2 = self.event.labelling_set.create(label=self.label2,
            creator=self.internal_user)

        # Remove label 2 and issue alerts
        lab2.delete()
        EventLabelAlertIssuer(lab2, alert_type='label_removed') \
            .issue_alerts()

        # Check recipients passed to email alert function
        email_recips = email_mock.call_args[0][2]
        self.assertEqual(email_recips.count(), 1)
        self.assertEqual(email_recips.first().description, 'label email')

        # Phone alerts should be called at all since there were no
        # verified recipients
        phone_mock.assert_not_called()
