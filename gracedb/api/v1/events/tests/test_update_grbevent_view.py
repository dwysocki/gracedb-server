try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import pytest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from guardian.shortcuts import assign_perm
from rest_framework.test import APIRequestFactory as rf

from events.models import Event, GrbEvent, Group, Pipeline, Search
from ..views import GrbEventPatchView
from ...settings import API_VERSION

UserModel = get_user_model()


###############################################################################
# UTILITIES ###################################################################
###############################################################################
def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


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
        codename='change_grbevent'
    )
    assign_perm(p, internal_group, grbevent)

    return grbevent


###############################################################################
# FIXTURES ####################################################################
###############################################################################


###############################################################################
# TESTS #######################################################################
###############################################################################
@pytest.mark.django_db
def test_access(internal_user, internal_group, standard_plus_grb_user):
    # NOTE: standard_plus_grb_user is a parametrized fixture (basically a
    #       list of three users), so this test will run three times.

    # Create a GrbEvent
    grbevent = create_grbevent(internal_group)

    # Get URL and set up request and view
    url = v_reverse("events:update-grbevent", args=[grbevent.graceid])
    data = {'redshift': 2}
    request = rf().patch(url, data=data)
    request.user = standard_plus_grb_user
    view = GrbEventPatchView.as_view()

    with mock.patch('gracedb.api.v1.events.views.EventAlertIssuer'):
        # Process request
        response = view(request, grbevent.graceid)
        response.render()

        # Update grbevent in memory from database
        grbevent.refresh_from_db()

    if standard_plus_grb_user.username != 'grb.user':
        assert response.status_code == 403
        assert grbevent.redshift is None
    else:
        assert response.status_code == 200
        assert grbevent.redshift == 2

@pytest.mark.parametrize("data",
    [
        {'redshift': 2, 't90': 12, 'designation': 'good'},
        {'ra': 1, 'dec': 2, 'error_radius': 3},
        # FAR should not be updated
        {'far': 123, 't90': 15},
    ]
)
@pytest.mark.django_db
def test_parameter_updates(grb_user, internal_group, data):
    grbevent = create_grbevent(internal_group)
    grbevent.far = 321
    grbevent.save(update_fields=['far'])

    # Get URL and set up request and view
    url = v_reverse("events:update-grbevent", args=[grbevent.graceid])
    request = rf().patch(url, data=data)
    request.user = grb_user
    view = GrbEventPatchView.as_view()

    with mock.patch('gracedb.api.v1.events.views.EventAlertIssuer'):
        # Process request
        response = view(request, grbevent.graceid)
        response.render()

        # Update grbevent in memory from database
        grbevent.refresh_from_db()

    # Check response
    assert response.status_code == 200

    # Compare parameters
    for attr in GrbEventPatchView.updatable_attributes:
        grbevent_attr = getattr(grbevent, attr)
        if attr in data:
            assert grbevent_attr == data.get(attr)
        else:
            assert grbevent_attr is None
    # FAR should not be updated even by requests which include FAR
    assert grbevent.far == 321


@pytest.mark.parametrize("data", [{}, {'redshift': 2}])
@pytest.mark.django_db
def test_update_with_no_new_data(grb_user, internal_group, data):
    grbevent = create_grbevent(internal_group)
    grbevent.redshift = 2
    grbevent.save(update_fields=['redshift'])

    # Get URL and set up request and view
    url = v_reverse("events:update-grbevent", args=[grbevent.graceid])
    request = rf().patch(url, data=data)
    request.user = grb_user
    view = GrbEventPatchView.as_view()

    with mock.patch('gracedb.api.v1.events.views.EventAlertIssuer'):
        # Process request
        response = view(request, grbevent.graceid)
        response.render()

    # Check response
    assert response.status_code == 400
    assert 'Request would not modify the GRB event' \
        in response.content.decode()


@pytest.mark.parametrize("data",
    [
        {'redshift': 'random string'},
        {'t90': 'random string'},
        {'ra': 'random string'},
        {'dec': 'random string'},
        {'error_radius': 'random string'},
    ]
)
@pytest.mark.django_db
def test_update_with_bad_data(grb_user, internal_group, data):
    grbevent = create_grbevent(internal_group)

    # Get URL and set up request and view
    url = v_reverse("events:update-grbevent", args=[grbevent.graceid])
    request = rf().patch(url, data=data)
    request.user = grb_user
    view = GrbEventPatchView.as_view()

    with mock.patch('gracedb.api.v1.events.views.EventAlertIssuer'):
        # Process request
        response = view(request, grbevent.graceid)
        response.render()

    # Check response
    assert response.status_code == 400
    assert 'must be a float' in response.content.decode()


@pytest.mark.django_db
def test_update_non_grbevent(grb_user, internal_group):
    event = Event.objects.create(
        submitter=grb_user,
        group=Group.objects.create(name='External'),
        pipeline=Pipeline.objects.create(name='other_pipeline'),
    )
    event.save()
    p, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Event),
        codename='change_event'
    )
    assign_perm(p, internal_group, event)

    # Get URL and set up request and view
    url = v_reverse("events:update-grbevent", args=[event.graceid])
    request = rf().patch(url, data={'redshift': 2})
    request.user = grb_user
    view = GrbEventPatchView.as_view()

    with mock.patch('gracedb.api.v1.events.views.EventAlertIssuer'):
        # Process request
        response = view(request, event.graceid)
        response.render()

    # Check response
    assert response.status_code == 400
    assert 'Cannot update GRB event parameters for non-GRB event' \
        in response.content.decode()
