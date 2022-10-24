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
    query: str
    query_type: str

    @classmethod
    @abstractmethod
    def setUpTestDataAndReturnQueryResult(cls):
        """
        Sets up the test database and returns the subset of created objects that
        should be returned by the query.  This is the only method that
        inheriting classes must implement.
        """
        ...

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Make sure the view_event permission exists
        ct = ContentType.objects.get_for_model(Event)
        p, _ = Permission.objects.get_or_create(codename='view_event',
            name='Can view event', content_type=ct)

        cls.expected_query_result = set(cls.setUpTestDataAndReturnQueryResult())

    def test_query(self):
        data = {
            'query': self.query,
            'query_type': self.query_type,
        }
        url = reverse('mainsearch')
        response = self.request_as_user(url, 'GET', self.internal_user,
            data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['objs']),
                         self.expected_query_result)

    @staticmethod
    def create_event(group_name, pipeline_name, gpstime, search_name=None,
        user=None):
        """
        """

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

        # Make data directory (should get removed at the end by
        # GraceDbTestBase tearDown function)
        os.makedirs(event.datadir)

        return event


class TestEmptyEventQuery(SearchViewTestMixin, GraceDbTestBase):
    query = ''
    query_type = 'E'

    @classmethod
    def setUpTestDataAndReturnQueryResult(cls):
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

        return [real_event1, real_event2]


class TestTestEventQuery(SearchViewTestMixin, GraceDbTestBase):
    query = 'Test'
    query_type = 'E'

    @classmethod
    def setUpTestDataAndReturnQueryResult(cls):
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

        return [test_event]


class TestMDCEventQuery(SearchViewTestMixin, GraceDbTestBase):
    query = 'MDC'
    query_type = 'E'

    @classmethod
    def setUpTestDataAndReturnQueryResult(cls):
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

        return [mdc_event]


class TestTestMDCEventQuery(SearchViewTestMixin, GraceDbTestBase):
    query = 'Test MDC'
    query_type = 'E'

    @classmethod
    def setUpTestDataAndReturnQueryResult(cls):
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

        return [test_mdc_event]
