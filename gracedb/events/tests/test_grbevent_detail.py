try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import pytest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from guardian.shortcuts import assign_perm

from events.models import Event, GrbEvent, Group, Pipeline, Search

UserModel = get_user_model()


###############################################################################
# UTILITIES ###################################################################
###############################################################################
def create_grbevent(internal_group):
    user = UserModel.objects.create(username='grbevent.creator')
    grb_search, _ = Search.objects.get_or_create(name='GRB')
    grbevent = GrbEvent.objects.create(
        submitter=user,
        group=Group.objects.create(name='External'),
        pipeline=Pipeline.objects.create(name=settings.GRB_PIPELINES[0]),
        search=grb_search
    )
    grbevent.save()
    p, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(GrbEvent),
        codename='view_grbevent'
    )
    assign_perm(p, internal_group, grbevent)

    return grbevent


###############################################################################
# FIXTURES ####################################################################
###############################################################################


###############################################################################
# TESTS #######################################################################
###############################################################################
# 1. Test that form shows up for authorized users for grbevents
# 2. Test that form doesn't show up for unauthorized users for grbevents
# 3. Test that form doesn't show up for authorized users and for non-grbevents
@pytest.mark.django_db
def test_view_access_and_context(internal_group, standard_plus_grb_user):
    # NOTE: standard_plus_grb_user is a parametrized fixture (basically a
    #       list of three users), so this test will run three times.

    # Create a GrbEvent
    grbevent = create_grbevent(internal_group)

    # Get URL and set up request and view
    url = reverse("view", args=[grbevent.graceid])
    c = Client()
    if not standard_plus_grb_user.is_anonymous:
        c.force_login(standard_plus_grb_user)

    with mock.patch('events.views.filter_events_for_user'):
        # Process request
        response = c.get(url)

    # Check response code
    if standard_plus_grb_user.is_anonymous:
        assert response.status_code == 403
    else:
        assert response.status_code == 200

        if standard_plus_grb_user.groups.filter(name='grb_managers').exists():
            assert response.context.get('can_update_grbevent', None) is True
            assert 'update_grbevent_form' in response.context
        else:
            assert response.context.get('can_update_grbevent', None) is False
            assert 'update_grbevent_form' not in response.context


@pytest.mark.django_db
def test_view_for_non_grbevent(internal_group, grb_user):
    event = Event.objects.create(
        submitter=grb_user,
        group=Group.objects.create(name='External'),
        pipeline=Pipeline.objects.create(name='other_pipeline'),
    )
    event.save()
    p, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Event),
        codename='view_event'
    )
    assign_perm(p, internal_group, event)

    # Get URL and set up request and view
    url = reverse("view", args=[event.graceid])
    c = Client()
    c.force_login(grb_user)

    with mock.patch('events.views.filter_events_for_user'):
        # Process request
        response = c.get(url)

    # Check response
    assert response.status_code == 200
    assert 'can_update_grbevent' not in response.context
    assert 'update_grbevent_form' not in response.context
