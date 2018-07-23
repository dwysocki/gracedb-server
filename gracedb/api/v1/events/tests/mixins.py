from __future__ import absolute_import
import os

from django.contrib.auth import get_user_model

from events.models import Event, Group, Pipeline, Search

UserModel = get_user_model()


class EventCreateMixin(object):

    @staticmethod
    def create_event(group_name, pipeline_name, search_name=None,
        user=None):
        """

        """

        # Create group, pipeline, and optionally, user
        group, _ = Group.objects.get_or_create(name=group_name)
        pipeline, _ = Pipeline.objects.get_or_create(name=pipeline_name)
        if user is None:
            user = UserModel.objects.create(username='event.user')

        # Compile event dict
        event_dict = {
            'group': group,
            'pipeline': pipeline,
            'submitter': user,
            'gpstime': 123,
        }

        # Set up search (if not None) and add to event_dict
        if search_name is not None:
            search, _ = Search.objects.get_or_create(name=search_name)
            event_dict['search'] = search

        # Create event and return
        event = Event.objects.create(**event_dict)

        # Make data directory (should get removed at the end by
        # GraceDbTestBase tearDown function)
        os.makedirs(event.datadir)

        return event
