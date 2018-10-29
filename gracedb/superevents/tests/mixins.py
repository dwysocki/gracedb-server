from __future__ import absolute_import
import os

from core.permission_utils import assign_perms_to_obj
from core.tests.utils import GraceDbTestBase
from events.tests.mixins import EventCreateMixin
from superevents.models import Superevent
from superevents.utils import expose_superevent, SUPEREVENT_PERMS


class SupereventCreateMixin(EventCreateMixin):

    @classmethod
    def create_superevent(cls, user, event_group='EventGroup',
        event_pipeline='EventPipeline', event_search='EventSearch',
        category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION):

        # Create event
        event = cls.create_event(event_group, event_pipeline, user=user,
            search_name=event_search)

        # Create superevent
        superevent = Superevent.objects.create(t_start=0, t_0=1, t_end=2,
            preferred_event=event, submitter=user, category=category)

        # Make data directory (should get removed at the end by
        # GraceDbTestBase tearDown function)
        os.makedirs(superevent.datadir)

        return superevent


class SupereventSetup(GraceDbTestBase, SupereventCreateMixin):
    """
    A base test class which creates superevents with specific
    view permissions.
    """

    @classmethod
    def setUpTestData(cls):
        super(SupereventSetup, cls).setUpTestData()

        # Create three superevents
        cls.internal_superevent = cls.create_superevent(cls.internal_user)
        cls.lvem_superevent = cls.create_superevent(cls.internal_user)
        cls.public_superevent = cls.create_superevent(cls.internal_user)

        # Expose one to LV-EM only - a little hacky since our utility
        # function for exposing a superevent only is capable of
        # exposing it to both LV-EM and the public.
        assign_perms_to_obj(SUPEREVENT_PERMS[cls.lvem_group.name],
            cls.lvem_group, cls.lvem_superevent)
        cls.lvem_superevent.is_exposed = True
        cls.lvem_superevent.save(update_fields=['is_exposed'])

        # Expose one to LV-EM and public, and assign relevant permissions
        expose_superevent(cls.public_superevent, cls.internal_user,
            add_log_message=False, issue_alert=False)
