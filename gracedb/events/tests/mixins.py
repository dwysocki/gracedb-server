from __future__ import absolute_import
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.contrib.contenttypes.models import ContentType

from core.tests.utils import GraceDbTestBase
from events.models import Event, Group, Pipeline, Search, Tag
from ..permission_utils import assign_default_event_perms
from ..views import update_event_perms_for_group

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
            user, _ = UserModel.objects.get_or_create(username='event.user')

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


class EventSetup(GraceDbTestBase, EventCreateMixin):
    """
    A base test class which creates events with specific
    view permissions.
    """

    @classmethod
    def setUpTestData(cls):
        super(EventSetup, cls).setUpTestData()

        # Create a few events
        cls.internal_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')
        cls.lvem_event = cls.create_event('EVENTGROUP', 'EVENTPIPELINE')

        # We need to make sure that the view_event permission exists
        # I guess since it's part of a data migration and not actually listed
        # in the 'Meta' class for the model, it's not preserved.
        ct = ContentType.objects.get_for_model(Event)
        p, _ = Permission.objects.get_or_create(codename='view_event',
            name='Can view event', content_type=ct)

        # Assign default permissions for internal group (also have to create
        # executives group because this perm assign code is TERRIBLE)
        execs, _ = AuthGroup.objects.get_or_create(name='executives')
        assign_default_event_perms(cls.internal_event)
        assign_default_event_perms(cls.lvem_event)

        # Expose one to LV-EM
        lvem_group = AuthGroup.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
        update_event_perms_for_group(cls.lvem_event, lvem_group, 'expose')


class ExposeLogMixin(object):

    @classmethod
    def expose_log_to_lvem(cls, log):
        lvem_tag, _ = Tag.objects.get_or_create(name='lvem')
        log.tags.add(lvem_tag)
