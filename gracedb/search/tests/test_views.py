import os
from unittest import mock

from abc import abstractmethod, ABCMeta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from core.tests.utils import GraceDbTestBase
from events.models import Event, Group, Label, Labelling, Pipeline, Search
from events.permission_utils import assign_default_event_perms
from superevents.models import Superevent
from superevents.utils import create_superevent


UserModel = get_user_model()


class SearchViewTestMixin(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def setUpTestDataAndReturnExampleQueries(cls):
        """
        Sets up the test database and returns a list of example queries and
        the subset of created objects that they should produce.

        Each example query should be a dict with the following entries:
        keys 'name', 'query',
        'query_type', and 'expected_result'.

        - name: used to refer to that specific test in any failed assertions
        - query: the query as one would enter in the search box
        - query_type: 'E' for events and 'S' for superevents
        - expected_result: a list containing a subset of the created DB objects
                           that should be produced by the query
        """
        ...

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Make sure the view_event permission exists
        ct = ContentType.objects.get_for_model(Event)
        p, _ = Permission.objects.get_or_create(codename='view_event',
            name='Can view event', content_type=ct)

        cls.example_queries = cls.setUpTestDataAndReturnExampleQueries()

    def test_query(self):
        for example in self.example_queries:
            name = example['name']
            query = example['query']
            query_type = example['query_type']
            expected_results = example['expected_results']

            data = {
                'query': query,
                'query_type': query_type,
            }
            url = reverse('mainsearch')
            response = self.request_as_user(url, 'GET', self.internal_user,
                data=data)

            msg = f"Failed on test '{name}'"
            self.assertEqual(response.status_code, 200, msg=msg)
            self.assertEqual(set(response.context['objs']),
                             set(expected_results),
                             msg=msg)

    @staticmethod
    def create_event(group_name, pipeline_name, gpstime, search_name=None,
        user=None):
        # Create group, pipeline, and optionally, user
        group, _ = Group.objects.get_or_create(name=group_name)
        pipeline, _ = Pipeline.objects.get_or_create(name=pipeline_name)
        if user is None:
            user, _ = UserModel.objects.get_or_create(username='event.user')

        # Compile event dict
        event_dict = {
            'group': group,
            'pipeline': pipeline,
            'submitter': user,
            'gpstime': gpstime,
        }

        # Set up search (if not None) and add to event_dict
        if search_name is not None:
            search, _ = Search.objects.get_or_create(name=search_name)
            event_dict['search'] = search

        # Create event
        event = Event.objects.create(**event_dict)

        # Assign default permissions for internal group
        assign_default_event_perms(event)

        # Save event to trigger field computation:
        event.save()

        return event

    @staticmethod
    def create_superevent(*, preferred_event, submitter, category,
                          events=None, labels=None,
                          t_start=0, t_0=1, t_end=2):
        if events is None:
            events = []
        if labels is None:
            labels = []

        return create_superevent(
            submitter=submitter, t_start=t_start, t_0=t_0, t_end=t_end,
            preferred_event=preferred_event, events=events, labels=labels,
            category=category, add_log_message=False, issue_alert=False)

    @staticmethod
    def create_label(name, description):
        return Label.objects.create(name=name, description=description)

    @staticmethod
    def apply_label(event, label, user=None):
        if user is None:
            user, _ = UserModel.objects.get_or_create(username='event.user')

        return event.labelling_set.create(label=label, creator=user)


class TestMinimalEventQueries(SearchViewTestMixin, GraceDbTestBase):
    @classmethod
    def setUpTestDataAndReturnExampleQueries(cls):
        real_event1 = cls.create_event(
            group_name='GROUP', pipeline_name='PIPELINE',
            gpstime=100, search_name='SEARCH')
        real_event2 = cls.create_event(
            group_name='GROUP', pipeline_name='PIPELINE',
            gpstime=101, search_name='SEARCH')

        test_event = cls.create_event(
            group_name='Test', pipeline_name='PIPELINE',
            gpstime=100, search_name='SEARCH')

        mdc_event = cls.create_event(
            group_name='GROUP', pipeline_name='PIPELINE',
            gpstime=100, search_name='MDC')

        test_mdc_event = cls.create_event(
            group_name='Test', pipeline_name='PIPELINE',
            gpstime=100, search_name='MDC')

        return [
            {'name': 'Empty event query',
             'query': '',
             'query_type': 'E',
             'expected_results': [real_event1, real_event2]},
            {'name': 'Test event query',
             'query': 'Test',
             'query_type': 'E',
             'expected_results': [test_event]},
            {'name': 'MDC event query',
             'query': 'MDC',
             'query_type': 'E',
             'expected_results': [mdc_event]},
            {'name': 'Test MDC event query',
             'query': 'Test MDC',
             'query_type': 'E',
             'expected_results': [test_mdc_event]},
        ]


def label_prefix_examples(examples):
    """
    Add 'label:' prefix to example label queries
    """
    return [
        {**example, 'query': f"label: {example['query']}"}
        for example in examples
    ]

def label_alt_AND_examples(examples):
    """
    Create additional example label queries using alternative AND characters
    """
    return [
        {**example, 'query': example['query'].replace('&', ',')}
        for example in examples
    ]

def label_alt_NOT_examples(examples):
    """
    Create additional example label queries using alternative NOT characters
    """
    return [
        {**example, 'query': example['query'].replace('~', '-')}
        for example in examples
    ]

def label_alt_examples(examples):
    """
    Create a comprehensive set of example label queries using equivalent
    alternative forms.
    """
    examples += label_prefix_examples(examples)

    return (
        examples +
        label_alt_AND_examples(examples) + label_alt_NOT_examples(examples)
    )


class TestLabeledEventQueries(SearchViewTestMixin, GraceDbTestBase):
    @classmethod
    def setUpTestDataAndReturnExampleQueries(cls):
        def make_event():
            return cls.create_event(
                group_name='GROUP', pipeline_name='PIPELINE',
                gpstime=100, search_name='SEARCH')

        def make_label(name):
            return cls.create_label(name=name, description=name)

        # Create events
        eventA = make_event()
        eventB = make_event()
        eventAB = make_event()
        eventUnlabeled = make_event()

        # Create labels
        labelA = make_label('A')
        labelB = make_label('B')

        # Apply labels to appropriate events
        cls.apply_label(eventA, labelA)
        cls.apply_label(eventB, labelB)
        cls.apply_label(eventAB, labelA)
        cls.apply_label(eventAB, labelB)

        # Create list of base examples
        examples = [
            {'name': 'Label A present',
             'query': 'A',
             'query_type': 'E',
             'expected_results': [eventA, eventAB]},
            {'name': 'Label B present',
             'query': 'B',
             'query_type': 'E',
             'expected_results': [eventB, eventAB]},
            {'name': 'Label A and B present',
             'query': 'A & B',
             'query_type': 'E',
             'expected_results': [eventAB]},
            {'name': 'Label A or B present',
             'query': 'A | B',
             'query_type': 'E',
             'expected_results': [eventA, eventB, eventAB]},
            {'name': 'Only label A present',
             'query': 'A & ~B',
             'query_type': 'E',
             'expected_results': [eventA]},
            {'name': 'Only label B present',
             'query': '~A & B',
             'query_type': 'E',
             'expected_results': [eventB]},
            {'name': 'Neither labels A or B present',
             'query': '~A & ~B',
             'query_type': 'E',
             'expected_results': [eventUnlabeled]},
            {'name': 'At least one of labels A or B is absent',
             'query': '~A | ~B',
             'query_type': 'E',
             'expected_results': [eventA, eventB, eventUnlabeled]},
        ]
        # Return base examples along with equivalent alternate forms
        return label_alt_examples(examples)


class TestLabeledSupereventQueries(SearchViewTestMixin, GraceDbTestBase):
    @classmethod
    def setUpTestDataAndReturnExampleQueries(cls):
        user, _ = UserModel.objects.get_or_create(username='event.user')

        def make_event():
            return cls.create_event(
                group_name='GROUP', pipeline_name='PIPELINE',
                gpstime=100, search_name='SEARCH')

        def make_superevent(*,
                            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
                            labels=None):
            return cls.create_superevent(preferred_event=make_event(),
                                         labels=labels, category=category,
                                         submitter=user)

        def make_label(name):
            return cls.create_label(name=name, description=name)

        # Create labels
        labelA = make_label('A')
        labelB = make_label('B')

        # Create superevents
        supereventA = make_superevent(labels=[labelA])
        supereventB = make_superevent(labels=[labelB])
        supereventAB = make_superevent(labels=[labelA, labelB])
        supereventUnlabeled = make_superevent()

        # Create list of base examples
        examples = [
            {'name': 'Label A present',
             'query': 'A',
             'query_type': 'S',
             'expected_results': [supereventA, supereventAB]},
            {'name': 'Label B present',
             'query': 'B',
             'query_type': 'S',
             'expected_results': [supereventB, supereventAB]},
            {'name': 'Label A and B present',
             'query': 'A & B',
             'query_type': 'S',
             'expected_results': [supereventAB]},
            {'name': 'Label A or B present',
             'query': 'A | B',
             'query_type': 'S',
             'expected_results': [supereventA, supereventB, supereventAB]},
            {'name': 'Only label A present',
             'query': 'A & ~B',
             'query_type': 'S',
             'expected_results': [supereventA]},
            {'name': 'Only label B present',
             'query': '~A & B',
             'query_type': 'S',
             'expected_results': [supereventB]},
            {'name': 'Neither labels A or B present',
             'query': '~A & ~B',
             'query_type': 'S',
             'expected_results': [supereventUnlabeled]},
            {'name': 'At least one of labels A or B is absent',
             'query': '~A | ~B',
             'query_type': 'S',
             'expected_results': [supereventA, supereventB,
                                  supereventUnlabeled]},
        ]
        # Return base examples along with equivalent alternate forms
        return label_alt_examples(examples)


class TestEventSupereventPairing(SearchViewTestMixin, GraceDbTestBase):
    @classmethod
    def setUpTestDataAndReturnExampleQueries(cls):
        user, _ = UserModel.objects.get_or_create(username='event.user')

        def make_event():
            return cls.create_event(
                group_name='GROUP', pipeline_name='PIPELINE',
                gpstime=100, search_name='SEARCH')

        def make_superevent(*, preferred_event,
                            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
                            events=None, labels=None):
            return cls.create_superevent(
                preferred_event=preferred_event, events=events, labels=labels,
                submitter=user, category=category)

        # Create two events under a superevent
        event1 = make_event()
        event2 = make_event()
        superevent = make_superevent(preferred_event=event1,
                                     events=[event1, event2])

        # Create an extra event and superevent which should not appear in any
        # results.
        event3 = make_event()
        superevent_other = make_superevent(preferred_event=event3)

        return [
            {'name': 'Event 1 presence',
             'query': f'event: {event1.graceid}',
             'query_type': 'S',
             'expected_results': [superevent]},
            {'name': 'Event 1 or 2 presence',
             'query': f'event: {event1.graceid} .. {event2.graceid}',
             'query_type': 'S',
             'expected_results': [superevent]},
            {'name': 'Preferred event presence',
             'query': f'preferred_event: {event1.graceid}',
             'query_type': 'S',
             'expected_results': [superevent]},
            {'name': 'Preferred event presence with extra event',
             'query': f'preferred_event: {event1.graceid} .. {event2.graceid}',
             'query_type': 'S',
             'expected_results': [superevent]},
        ]
