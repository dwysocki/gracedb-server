import os
from unittest import mock

from abc import abstractmethod, ABCMeta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from core.tests.utils import GraceDbTestBase
from events.models import Event, Group, Label, Pipeline, Search
from events.permission_utils import assign_default_event_perms
from superevents.models import Superevent


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
