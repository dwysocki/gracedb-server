from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings

from events.models import Group as SGroup, Pipeline, Search, Event
from superevents.forms import SupereventForm

UserModel = get_user_model()

@override_settings(
    SEND_XMPP_ALERTS = False,
    SEND_PHONE_ALERTS = False,
    SEND_EMAIL_ALERTS = False,
)
class TestSupereventForm(TestCase):
    """
    Test the use of a model form for validating model data and
    creating/updating model instances.

    This is also somewhat of a test of the model itself, at least in terms
    of field and overall model validation.
    """
    nEvents = 10

    @classmethod
    def setUpTestData(cls):

        # Set up a user for event creation
        cls.user, _ = UserModel.objects.get_or_create(username='TestUser')

        # Set up group, pipeline, and search for event creation
        cls.ev_group, _ = SGroup.objects.get_or_create(name='GWGroup')
        cls.ext_group, _ = SGroup.objects.get_or_create(name=settings.EXTERNAL_ANALYSIS_GROUP)
        cls.ev_pipeline, _ = Pipeline.objects.get_or_create(name='GWPipeline')
        cls.ev_search, _ = Search.objects.get_or_create(name='GWSearch')

        # Create several events
        for i in range(cls.nEvents):
            Event.objects.create(group=cls.ev_group, pipeline=cls.ev_pipeline,
                search=cls.ev_search, gpstime=0, submitter=cls.user)

        # Create an external event
        cls.ext_event = Event.objects.create(group=cls.ext_group,
            pipeline=cls.ev_pipeline, search=cls.ev_search, gpstime=0,
            submitter=cls.user)

        # Get a list of gw events
        cls.gw_events = Event.objects.filter(group__name=cls.ev_group.name)

    def test_form_correct(self):
        """Test form with correct input data"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': submitter.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertTrue(form.is_valid())

        # Make sure submitter field is set correctly
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # Make sure preferred_event is set correctly
        self.assertEqual(preferred_event, form.cleaned_data['preferred_event'])

        # Make sure events are set correctly
        self.assertEqual(events.count(), form.cleaned_data['events'].count())
        for ev in events:
            self.assertIn(ev, form.cleaned_data['events'])

    def test_form_correct_no_events(self):
        """Test form with correct input data (no events)"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        data_dict = {
            'submitter': submitter.username,
            'preferred_event': preferred_event.graceid(),
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertTrue(form.is_valid())

        # Make sure submitter field is set correctly
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # Make sure preferred_event is set correctly
        self.assertEqual(preferred_event, form.cleaned_data['preferred_event'])

        # events queryset should be empty
        self.assertTrue(form.cleaned_data['events'].count() == 0)

    def test_form_correct_no_preferred_event(self):
        """Test form with correct input data (no preferred_event)"""
        submitter = self.user
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': submitter.username,
            'events': [ev.graceid() for ev in events]
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertTrue(form.is_valid())

        # Make sure submitter field is set correctly
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # preferred_event should be None
        self.assertTrue(form.cleaned_data['preferred_event'] is None)

        # Make sure events are set correctly
        self.assertEqual(events.count(), form.cleaned_data['events'].count())
        for ev in events:
            self.assertIn(ev, form.cleaned_data['events'])

    def test_form_no_preferred_event_no_events(self):
        """Test form with no preferred_event or events"""
        submitter = self.user
        data_dict = {
            'submitter': submitter.username,
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertFalse(form.is_valid())

        # Submitter should be correct
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # preferred_event should be None
        self.assertTrue(form.cleaned_data['preferred_event'] is None)

        # events queryset should be empty
        self.assertTrue(form.cleaned_data['events'].count() == 0)

        # Check that errors dictionary is what we expect
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue(form.errors.has_key('__all__'))
        self.assertTrue(len(form.errors['__all__']) == 1)
        self.assertEqual(form.errors['__all__'][0],
            SupereventForm.error_messages['event_missing'])

    def test_bad_submitter(self):
        """Test form with non-existent user"""
        submitter_name = 'BadUser'
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': submitter_name,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertFalse(form.is_valid())

        # Make sure submitter field is set correctly
        self.assertFalse(form.cleaned_data.has_key('submitter'))

        # Make sure form errors are what we expect
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue(form.errors.has_key('submitter'))

        # Make sure preferred_event is set correctly
        self.assertEqual(preferred_event, form.cleaned_data['preferred_event'])

        # Make sure events are set correctly
        self.assertEqual(events.count(), form.cleaned_data['events'].count())
        for ev in events:
            self.assertIn(ev, form.cleaned_data['events'])

    def test_bad_events(self):
        """Test form with non-existent event"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': self.user.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events] + ['G123456']
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertFalse(form.is_valid())

        # Submitter should be correct
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # Make sure preferred_event is set correctly
        self.assertEqual(preferred_event, form.cleaned_data['preferred_event'])

        # Make sure events are set correctly
        self.assertFalse(form.cleaned_data.has_key('events'))

        # Make sure form errors are what we expect
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue(form.errors.has_key('events'))

    def test_external_preferred_event(self):
        """Test external event as preferred"""
        submitter = self.user
        preferred_event = self.ext_event
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': self.user.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertFalse(form.is_valid())

        # Submitter should be correct
        self.assertEqual(submitter, form.cleaned_data['submitter'])

        # Make sure preferred_event is set correctly
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue(form.errors.has_key('preferred_event'))

        # Make sure events are set correctly
        self.assertEqual(events.count(), form.cleaned_data['events'].count())
        for ev in events:
            self.assertIn(ev, form.cleaned_data['events'])

    def test_save_object(self):
        """Test saving superevent instance from form data"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': self.user.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create form from data
        form = SupereventForm(data_dict)

        # Form is valid?
        self.assertTrue(form.is_valid())

        # Try to save the object
        obj = form.save()

        # Check object attributes
        self.assertEqual(submitter, obj.submitter)
        self.assertEqual(preferred_event, obj.preferred_event)
        # +1 because object events list includes preferred_event
        self.assertEqual(events.count() + 1, obj.events.count())
        for ev in events:
            self.assertIn(ev, obj.events.all())

    def test_duplicate_preferred_event(self):
        """Test creation of two superevents with same preferred event"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': self.user.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create first superevent
        form = SupereventForm(data_dict)
        self.assertTrue(form.is_valid())
        obj1 = form.save()

        # Try to create second one
        events2 = self.gw_events.all()[5:6]
        data_dict['events'] = [ev.graceid() for ev in events2]
        form2 = SupereventForm(data_dict)

        # Check form errors and data
        self.assertFalse(form2.is_valid())
        self.assertEqual(submitter, form2.cleaned_data['submitter'])
        self.assertTrue(len(form2.errors) == 1)
        self.assertTrue(form2.errors.has_key('preferred_event'))
        self.assertEqual(events2.count(), form2.cleaned_data['events'].count())
        for ev in events2:
            self.assertIn(ev, form2.cleaned_data['events'])

        # Make sure that save fails for invalid form
        with self.assertRaises(ValueError):
            form2.save()

    def test_duplicate_event(self):
        """Test creation with event already assigned to superevent"""
        submitter = self.user
        preferred_event = self.gw_events.first()
        events = self.gw_events.all()[1:4]
        data_dict = {
            'submitter': self.user.username,
            'preferred_event': preferred_event.graceid(),
            'events': [ev.graceid() for ev in events]
        }

        # Create first superevent
        form = SupereventForm(data_dict)
        self.assertTrue(form.is_valid())
        obj1 = form.save()

        # Try to create second superevent, using two events that were
        # assigned to the first one.
        preferred_event2 = self.gw_events.last()
        events2 = self.gw_events.all()[2:5]
        data_dict['preferred_event'] = preferred_event2.graceid()
        data_dict['events'] = [ev.graceid() for ev in events2]
        form2 = SupereventForm(data_dict)

        # Check form errors and data
        self.assertFalse(form2.is_valid())
        self.assertEqual(submitter, form2.cleaned_data['submitter'])
        self.assertEqual(preferred_event2,
            form2.cleaned_data['preferred_event'])
        self.assertTrue(len(form2.errors) == 1)
        self.assertTrue(form2.errors.has_key('events'))
        self.assertTrue(len(form2.errors['events']) == 2)

        # Make sure that save fails for invalid form
        with self.assertRaises(ValueError):
            form2.save()

    def test_update_object_with_form(self):
        print("\n\nWARNING: NOT IMPLEMENTED\n\n")
