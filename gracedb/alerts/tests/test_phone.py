import mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils.http import urlencode

from alerts.models import Contact
from alerts.phone import (
    get_message_content, compile_twiml_url, issue_phone_alerts,
)
from alerts.utils import convert_superevent_id_to_speech
from core.tests.utils import GraceDbTestBase
from core.time_utils import gpsToUtc
from core.urls import build_absolute_uri
from events.models import Label
from superevents.tests.mixins import SupereventCreateMixin


class TestMessageContent(GraceDbTestBase, SupereventCreateMixin):
    """Test content sent in text message alerts"""

    @classmethod
    def setUpTestData(cls):
        super(TestMessageContent, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        cls.event = cls.superevent.preferred_event

        # Create a label
        cls.label, _ = Label.objects.get_or_create(name='TEST_LABEL1')

    def test_new_event(self):
        """Test message contents for new event alert"""
        message = get_message_content(self.event, 'new')

        # Check content
        expected = 'A {pipeline} event with GraceDB ID {gid} was created' \
            .format(pipeline=self.event.pipeline.name, gid=self.event.graceid)
        expected_url = build_absolute_uri(reverse('view',
            args=[self.event.graceid]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_update_event(self):
        """Test message contents for event update alert"""
        message = get_message_content(self.event, 'update')

        # Check content
        expected = 'A {pipeline} event with GraceDB ID {gid} was updated' \
            .format(pipeline=self.event.pipeline.name, gid=self.event.graceid)
        expected_url = build_absolute_uri(reverse('view',
            args=[self.event.graceid]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_label_added_event(self):
        """Test message contents for label_added event alert"""
        message = get_message_content(self.event, 'label_added',
            label=self.label)

        # Check content
        expected = ('A {pipeline} event with GraceDB ID {gid} was labeled '
            'with {label}').format(pipeline=self.event.pipeline.name,
            label=self.label.name, gid=self.event.graceid)
        expected_url = build_absolute_uri(reverse('view',
            args=[self.event.graceid]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_label_removed_event(self):
        """Test message contents for label_removed event alert"""
        message = get_message_content(self.event, 'label_removed',
            label=self.label)

        # Check content
        expected = ('The label {label} was removed from a {pipeline} event '
            'with GraceDB ID {gid}').format(pipeline=self.event.pipeline.name,
            label=self.label.name, gid=self.event.graceid)
        expected_url = build_absolute_uri(reverse('view',
            args=[self.event.graceid]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_new_superevent(self):
        """Test message contents for new superevent alert"""
        message = get_message_content(self.superevent, 'new')

        # Check content
        expected = 'A superevent with GraceDB ID {sid} was created'.format(
            sid=self.superevent.superevent_id)
        expected_url = build_absolute_uri(reverse('superevents:view',
            args=[self.superevent.superevent_id]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_update_superevent(self):
        """Test message contents for superevent update alert"""
        message = get_message_content(self.superevent, 'update')

        # Check content
        expected = 'A superevent with GraceDB ID {sid} was updated'.format(
            sid=self.superevent.superevent_id)
        expected_url = build_absolute_uri(reverse('superevents:view',
            args=[self.superevent.superevent_id]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_label_added_superevent(self):
        """Test message contents for label_added superevent alert"""
        message = get_message_content(self.superevent, 'label_added',
            label=self.label)

        # Check content
        expected = ('A superevent with GraceDB ID {sid} was labeled '
            'with {label}').format(sid=self.superevent.superevent_id,
            label=self.label.name)
        expected_url = build_absolute_uri(reverse('superevents:view',
            args=[self.superevent.superevent_id]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)

    def test_label_removed_superevent(self):
        """Test message contents for label_removed superevent alert"""
        message = get_message_content(self.superevent, 'label_removed',
            label=self.label)

        # Check content
        expected = ('The label {label} was removed from a superevent with '
            'GraceDB ID {sid}').format(sid=self.superevent.superevent_id,
            label=self.label.name)
        expected_url = build_absolute_uri(reverse('superevents:view',
            args=[self.superevent.superevent_id]))
        self.assertIn(expected, message)
        self.assertIn(expected_url, message)


class TestTwimlUrl(GraceDbTestBase, SupereventCreateMixin):
    """Test content sent in text message alerts"""

    @classmethod
    def setUpTestData(cls):
        super(TestTwimlUrl, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        cls.event = cls.superevent.preferred_event

        # Create a label
        cls.label, _ = Label.objects.get_or_create(name='TEST_LABEL1')

    def test_new_event(self):
        """Test TwiML URL for new event alert"""
        url = compile_twiml_url(self.event, 'new')

        # Compile expected URL
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['new'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_update_event(self):
        """Test TwiML URL for event update alert"""
        url = compile_twiml_url(self.event, 'update')

        # Compile expected URL
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['update'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_label_added_event(self):
        """Test TwiML URL for label_added event alert"""
        url = compile_twiml_url(self.event, 'label_added',
            label=self.label.name)

        # Compile expected URL
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['label_added'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_label_removed_event(self):
        """Test TwiML URL for label_removed event alert"""
        url = compile_twiml_url(self.event, 'label_removed',
        label=self.label.name)

        # Compile expected URL
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['label_removed'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_new_superevent(self):
        """Test TwiML URL for new superevent alert"""
        url = compile_twiml_url(self.superevent, 'new')

        # Compile expected URL
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['new'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_update_superevent(self):
        """Test TwiML URL for superevent update alert"""
        url = compile_twiml_url(self.superevent, 'update')

        # Compile expected URL
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['update'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_label_added_superevent(self):
        """Test TwiML URL for label_added superevent alert"""
        url = compile_twiml_url(self.superevent, 'label_added',
            label=self.label.name)

        # Compile expected URL
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['label_added'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)

    def test_label_removed_superevent(self):
        """Test TwiML URL for label_removed superevent alert"""
        url = compile_twiml_url(self.superevent, 'label_removed',
            label=self.label.name)

        # Compile expected URL
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['label_removed'],
            params=urlencode(urlparams))
        # Check URL
        self.assertEqual(expected_url, url)


@mock.patch('alerts.phone.twilio_client.messages.create')
@mock.patch('alerts.phone.twilio_client.calls.create')
class TestPhoneCallAndText(GraceDbTestBase, SupereventCreateMixin):

    @classmethod
    def setUpTestData(cls):
        super(TestPhoneCallAndText, cls).setUpTestData()

        # Create a superevent
        cls.superevent = cls.create_superevent(cls.internal_user,
            'fake_group', 'fake_pipeline', 'fake_search')

        # References to cls/self.event will refer to the superevent's
        cls.event = cls.superevent.preferred_event

        # Create a label
        cls.label, _ = Label.objects.get_or_create(name='TEST_LABEL1')

        # Create a few phone contacts
        cls.contact1 = Contact.objects.create(user=cls.internal_user,
            description='contact1', phone='12345678901', verified=True,
            phone_method=Contact.CONTACT_PHONE_CALL)
        cls.contact2 = Contact.objects.create(user=cls.internal_user,
            description='contact2', phone='12345654321', verified=True,
            phone_method=Contact.CONTACT_PHONE_BOTH)
        cls.contacts = Contact.objects.filter(pk__in=[cls.contact1.pk,
            cls.contact2.pk])

        # Refresh from DB to pull formatted phone numbers
        cls.contact1.refresh_from_db()
        cls.contact2.refresh_from_db()

    def test_new_superevent(self, mock_call, mock_text):
        """Test issuing phone alerts for new superevent alert"""
        issue_phone_alerts(self.superevent, 'new', self.contacts)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)

        # Check URLs
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['new'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_update_superevent(self, mock_call, mock_text):
        """Test issuing phone alerts for superevent update alert"""
        issue_phone_alerts(self.superevent, 'update', self.contacts)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)
        # Check URLs
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['update'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_label_added_superevent(self, mock_call, mock_text):
        """Test issuing phone alerts for label_added superevent alert"""
        issue_phone_alerts(self.superevent, 'label_added', self.contacts,
            label=self.label)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)
        # Check URLs
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['label_added'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_label_removed_superevent(self, mock_call, mock_text):
        """Test issuing phone alerts for label_removed superevent alert"""
        issue_phone_alerts(self.superevent, 'label_removed', self.contacts,
            label=self.label)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)
        # Check URLs
        urlparams = {
            'sid': convert_superevent_id_to_speech(
                self.superevent.superevent_id),
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['superevent']['label_removed'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_new_event(self, mock_call, mock_text):
        """Test issuing phone alerts for new event alert"""
        issue_phone_alerts(self.event, 'new', self.contacts)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)

        # Check URLs
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['new'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_update_event(self, mock_call, mock_text):
        """Test issuing phone alerts for event update alert"""
        issue_phone_alerts(self.event, 'update', self.contacts)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)

        # Check URLs
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['update'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_label_added_event(self, mock_call, mock_text):
        """Test issuing phone alerts for label_added event alert"""
        issue_phone_alerts(self.event, 'label_added', self.contacts,
            self.label)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)

        # Check URLs
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['label_added'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)

    def test_label_removed_event(self, mock_call, mock_text):
        """Test issuing phone alerts for label_removed event alert"""
        issue_phone_alerts(self.event, 'label_removed', self.contacts,
            self.label)

        # Check calls
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][1]['to'],
            self.contact1.phone)
        self.assertEqual(mock_call.call_args_list[1][1]['to'],
            self.contact2.phone)

        # Check texts
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args[1]['to'],
            self.contact2.phone)

        # Check URLs
        urlparams = {
            'graceid': self.event.graceid,
            'pipeline': self.event.pipeline.name,
            'label_lower': self.label.name.lower(),
        }
        expected_url = '{base}{twiml_bin}?{params}'.format(
            base=settings.TWIML_BASE_URL,
            twiml_bin=settings.TWIML_BIN['event']['label_removed'],
            params=urlencode(urlparams))
        # Check URL
        for call_args in mock_call.call_args_list:
            self.assertEqual(call_args[1]['url'], expected_url)
