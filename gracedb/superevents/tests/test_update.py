try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import time

import pytest

from events.models import Event, Group, Pipeline
from superevents.models import Superevent
from superevents.utils import update_superevent


# Can fail, mostly we want this test to exist so we can have some
# indication if it starts failing consistently and have some idea
# of what the execution time is
@pytest.mark.xfail
def test_update_superevent_execution_time(internal_user):
    # Create two events
    group, _ = Group.objects.get_or_create(name='event_group')
    pipeline, _ = Pipeline.objects.get_or_create(name='event_pipeline')
    event1 = Event.objects.create(group=group, pipeline=pipeline,
                                  far=1, submitter=internal_user)
    event2 = Event.objects.create(group=group, pipeline=pipeline,
                                  far=1, submitter=internal_user)

    # Create a superevent
    s = Superevent.objects.create(
        t_start=1, t_0=2, t_end=3, submitter=internal_user,
        preferred_event=event1,
    )

    # Update it
    t1 = time.time()
    update_superevent(
        s, internal_user, add_log_message=True, issue_alert=False,
        t_start=11, t_0=12, t_end=13, preferred_event=event2
    )
    t2 = time.time()

    # Enforce execution time
    assert (t2 - t1) < 0.05
