from django.conf import settings
from django.contrib.auth.models import Group as DjangoGroup, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils.http import urlencode

from core.tests.utils import GraceDbTestBase
from events.models import Event
from events.permission_utils import assign_default_event_perms
from events.tests.mixins import EventCreateMixin
from events.views import update_event_perms_for_group
from superevents.models import Superevent
from superevents.tests.mixins import SupereventSetup
from ..forms import MainSearchForm


class SearchTestingBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(SearchTestingBase, cls).setUpClass()
        cls.url = reverse('mainsearch')


class TestEventSearch(EventCreateMixin, GraceDbTestBase, SearchTestingBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventSearch, cls).setUpClass()
        # Set up query for production events
        cls.query_dict = {
            'query': '',
            'query_type': MainSearchForm.QUERY_TYPE_EVENT,
            'results_format': MainSearchForm.FORMAT_CHOICE_STANDARD,
        }
        cls.full_url = cls.url + '?' + urlencode(cls.query_dict)

    @classmethod
    def setUpTestData(cls):
        super(TestEventSearch, cls).setUpTestData()
        # Create a few events
        cls.internal_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')
        cls.lvem_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')

        # We need to make sure that the view_event permission exists
        # I guess since it's part of a data migration and not actually listed
        # in the 'Meta' class for the model, it's not preserved..
        ct = ContentType.objects.get_for_model(Event)
        p, _ = Permission.objects.get_or_create(codename='view_event',
            name='Can view event', content_type=ct)

        # Assign default permissions for internal group (also have to create
        # executives group because this perm assign code is TERRIBLE)
        execs, _ = DjangoGroup.objects.get_or_create(name='executives')
        assign_default_event_perms(cls.internal_event)
        assign_default_event_perms(cls.lvem_event)

        # Expose events
        lvem_group = DjangoGroup.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
        update_event_perms_for_group(cls.lvem_event, lvem_group, 'expose')

    def test_internal_user_search(self):
        """Internal user sees all events in search results"""
        response = self.request_as_user(self.full_url, "GET",
            self.internal_user)
        # Response status
        self.assertEqual(response.status_code, 200)
        # Make sure all events are shown
        for e in Event.objects.all():
            self.assertIn(e, response.context['objs'])

    def test_lvem_user_search(self):
        """LV-EM user sees only exposed superevents in search results"""
        response = self.request_as_user(self.full_url, "GET",
            self.lvem_user)
        # Response status
        self.assertEqual(response.status_code, 200)
        # Make sure only exposed events are shown
        self.assertIn(self.lvem_event, response.context['objs'])
        self.assertEqual(len(response.context['objs']), 1)

    def test_public_user_search(self):
        """
        Public user sees NO events since we don't expose them publicly
        at present
        """
        response = self.request_as_user(self.full_url, "GET")
        # Response status
        self.assertEqual(response.status_code, 200)
        # Make sure only exposed events are shown
        self.assertEqual(len(response.context['objs']), 0)


class TestSupereventSearch(SupereventSetup, GraceDbTestBase,
    SearchTestingBase):

    @classmethod
    def setUpClass(cls):
        super(TestSupereventSearch, cls).setUpClass()
        # Set up query for production superevents
        cls.query_dict = {
            'query': 'Production',
            'query_type': MainSearchForm.QUERY_TYPE_SUPEREVENT,
            'results_format': MainSearchForm.FORMAT_CHOICE_STANDARD,
        }
        cls.full_url = cls.url + '?' + urlencode(cls.query_dict)

    def test_internal_user_search(self):
        """Internal user sees all superevents in search results"""
        response = self.request_as_user(self.full_url, "GET",
            self.internal_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure all superevents are shown
        for s in Superevent.objects.all():
            self.assertIn(s, response.context['objs'])

    def test_lvem_user_search(self):
        """LV-EM user sees only exposed superevents in search results"""
        response = self.request_as_user(self.full_url, "GET",
            self.lvem_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed superevents are shown
        self.assertIn(self.lvem_superevent, response.context['objs'])
        self.assertIn(self.public_superevent, response.context['objs'])
        self.assertEqual(len(response.context['objs']), 2)

    def test_public_user_search(self):
        """Public user sees only exposed superevents in search results"""
        response = self.request_as_user(self.full_url, "GET")
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed superevents are shown
        self.assertIn(self.public_superevent, response.context['objs'])
        self.assertEqual(len(response.context['objs']), 1)


class TestEventLatest(EventCreateMixin, GraceDbTestBase):
    """Test which events are shown on 'latest' page for events"""

    @classmethod
    def setUpClass(cls):
        super(TestEventLatest, cls).setUpClass()
        # Set up query for production events
        cls.query_dict = {
            'query': '',
            'query_type': MainSearchForm.QUERY_TYPE_EVENT,
            'results_format': MainSearchForm.FORMAT_CHOICE_STANDARD,
        }
        cls.url = reverse('latest')
        cls.full_url = cls.url + '?' + urlencode(cls.query_dict)

    @classmethod
    def setUpTestData(cls):
        super(TestEventLatest, cls).setUpTestData()
        # Create a few events
        cls.internal_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')
        cls.lvem_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')

        # We need to make sure that the view_event permission exists
        # I guess since it's part of a data migration and not actually listed
        # in the 'Meta' class for the model, it's not preserved..
        ct = ContentType.objects.get_for_model(Event)
        p, _ = Permission.objects.get_or_create(codename='view_event',
            name='Can view event', content_type=ct)

        # Assign default permissions for internal group (also have to create
        # executives group because this perm assign code is TERRIBLE)
        execs, _ = DjangoGroup.objects.get_or_create(name='executives')
        assign_default_event_perms(cls.internal_event)
        assign_default_event_perms(cls.lvem_event)

        # Expose an event to LV-EM
        lvem_group = DjangoGroup.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
        update_event_perms_for_group(cls.lvem_event, lvem_group, 'expose')

    def test_internal_user_latest(self):
        """Internal user sees all events on latest page"""
        response = self.request_as_user(self.full_url, "GET",
            self.internal_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure all events are shown
        self.assertIn('events', response.context.keys())
        for e in Event.objects.all():
            self.assertIn(e, response.context['events'])

    def test_lvem_user_latest(self):
        """LV-EM user sees only exposed superevents on latest page"""
        response = self.request_as_user(self.full_url, "GET",
            self.lvem_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed events are shown
        self.assertIn('events', response.context.keys())
        self.assertIn(self.lvem_event, response.context['events'])
        self.assertEqual(len(response.context['events']), 1)

    def test_public_user_latest(self):
        """
        Public user sees NO events on latest page since we don't expose events
        publicly at the moment
        """
        response = self.request_as_user(self.full_url, "GET")
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed events are shown
        self.assertIn('events', response.context.keys())
        self.assertEqual(len(response.context['events']), 0)


class TestSupereventLatest(SupereventSetup, GraceDbTestBase):
    """Test which superevents are shown on 'latest' page for superevents"""

    @classmethod
    def setUpClass(cls):
        super(TestSupereventLatest, cls).setUpClass()
        # Set up query for production superevents
        cls.query_dict = {
            'query': '',
            'query_type': MainSearchForm.QUERY_TYPE_SUPEREVENT,
            'results_format': MainSearchForm.FORMAT_CHOICE_STANDARD,
        }
        cls.url = reverse('latest')
        cls.full_url = cls.url + '?' + urlencode(cls.query_dict)

    def test_internal_user_latest(self):
        """Internal user sees all superevents on latest page"""
        response = self.request_as_user(self.full_url, "GET",
            self.internal_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure all superevents are shown
        self.assertIn('superevents', response.context.keys())
        for s in Superevent.objects.all():
            self.assertIn(s, response.context['superevents'])

    def test_lvem_user_latest(self):
        """LV-EM user sees only exposed superevents on latest page"""
        response = self.request_as_user(self.full_url, "GET",
            self.lvem_user)
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed superevents are shown
        self.assertIn('superevents', response.context.keys())
        self.assertIn(self.lvem_superevent, response.context['superevents'])
        self.assertIn(self.public_superevent, response.context['superevents'])
        self.assertEqual(len(response.context['superevents']), 2)

    def test_public_user_latest(self):
        """Public user sees only exposed superevents on latest page"""
        response = self.request_as_user(self.full_url, "GET")
        # Response status
        self.assertEqual(response.status_code, 200) 
        # Make sure only exposed superevents are shown
        self.assertIn('superevents', response.context.keys())
        self.assertIn(self.public_superevent, response.context['superevents'])
        self.assertEqual(len(response.context['superevents']), 1)
