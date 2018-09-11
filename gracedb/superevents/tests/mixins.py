from __future__ import absolute_import
import os

from django.contrib.auth import get_user_model

from events.tests.mixins import EventCreateMixin
from ..models import Superevent

UserModel = get_user_model()


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
