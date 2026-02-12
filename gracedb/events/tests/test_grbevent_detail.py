try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
from importlib import resources
import os
import pytest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from guardian.models import UserObjectPermission
from guardian.shortcuts import assign_perm

from . import data
from events.models import Event, GrbEvent, Group, Pipeline, Search
from events.translator import handle_uploaded_data

UserModel = get_user_model()


###############################################################################
# UTILITIES ###################################################################
###############################################################################
def create_grbevent(internal_group, pipeline=settings.GRB_PIPELINES[0]):
    user = UserModel.objects.create(username='grbevent.creator')
    grb_search, _ = Search.objects.get_or_create(name='GRB')
    grbevent = GrbEvent.objects.create(
        submitter=user,
        group=Group.objects.create(name='External'),
        pipeline=Pipeline.objects.create(name=pipeline),
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


@pytest.mark.parametrize('filename',
                         ['fermi_grb_gcn.xml',
                          'fermi_subgrb_gcn.xml',
                          'swift_grb_gcn.xml',
                          'snews_gcn.xml',
                          'kafka_alert_fermi_gbm_alert.json',
                          'kafka_alert_fermi_flight.json',
                          'kafka_alert_fermi_ground.json',
                          'kafka_alert_fermi_final.json',
                          'kafka_alert_fermi_subgrbtargeted.json',
                          'kafka_alert_swift_subgrbtargeted_initial.json',
                          'kafka_alert_swift_subgrbtargeted_update.json',
                          'kafka_alert_svom_wakeup.json',
                          'kafka_alert_icecube_bronze.json',
                          'kafka_alert_chime_detection.json'])
                          # FIXME: Add examples when Rubin and EinsteinProbe
                          # are officially added
                          #'kafka_alert_einsteinprobe.json'
                          #'kafka_alert_rubin.json'
@pytest.mark.django_db
def test_external_event_creation(internal_group, standard_plus_grb_user,
                                 filename):
    """Only specific users should be able to create non-Test events"""

    pipelines = {
        'fermi': 'Fermi',
        'swift': 'Swift',
        'svom': 'SVOM',
        'icecube': 'IceCube',
        'einsteinprobe': 'EinsteinProbe',
        'chime': 'CHIME',
        'rubin': 'Rubin',
        'snews': 'SNEWS'
    }

    pipeline = None
    for key, val in pipelines.items():
        if key in filename:
            pipeline = val
            break

    event = create_grbevent(internal_group, pipeline=pipeline)

    file_path = resources.files(data).joinpath(filename)

    handle_uploaded_data(event, file_path)

    no_skymap_info = \
        'gbm_alert' in filename or 'subgrbtargeted_initial' in filename

    assert event.trigger_id is not None
    assert event.gpstime is not None
    if no_skymap_info:
        assert event.ra is None
        assert event.dec is None
    else:
        assert event.ra is not None
        assert event.dec is not None
    # Make sure Rubin gets a zero error radius
    if pipeline == 'Rubin' or no_skymap_info:
        assert event.error_radius is None
    else:
        assert event.error_radius is not None


@pytest.mark.parametrize('filename',
                         ['fermi_grb_gcn.xml',
                          'fermi_subgrb_gcn.xml',
                          'swift_grb_gcn.xml',
                          'snews_gcn.xml',
                          'kafka_alert_fermi_gbm_alert.json',
                          'kafka_alert_fermi_flight.json',
                          'kafka_alert_fermi_ground.json',
                          'kafka_alert_fermi_final.json',
                          'kafka_alert_fermi_subgrbtargeted.json',
                          'kafka_alert_swift_subgrbtargeted_initial.json',
                          'kafka_alert_swift_subgrbtargeted_update.json',
                          'kafka_alert_svom_wakeup.json',
                          'kafka_alert_icecube_bronze.json',
                          'kafka_alert_chime_detection.json'])
@pytest.mark.django_db
def test_external_event_creation_http(internal_group, grb_user, filename,
                                      tmp_path, settings):
    """Test external event creation via HTTP POST and verify the detail view."""

    pipelines = {
        'fermi': 'Fermi',
        'swift': 'Swift',
        'svom': 'SVOM',
        'icecube': 'IceCube',
        'einsteinprobe': 'EinsteinProbe',
        'chime': 'CHIME',
        'rubin': 'Rubin',
        'snews': 'SNEWS'
    }

    pipeline_name = None
    for key, val in pipelines.items():
        if key in filename:
            pipeline_name = val
            break

    # Set up DB objects
    Group.objects.get_or_create(name='External')
    pipeline, _ = Pipeline.objects.get_or_create(name=pipeline_name)
    Search.objects.get_or_create(name='GRB')
    AuthGroup.objects.get_or_create(name=settings.EXEC_GROUP)

    # Grant populate_pipeline permission to grb_user on this pipeline
    ctype = ContentType.objects.get_for_model(Pipeline)
    perm, _ = Permission.objects.get_or_create(
        codename='populate_pipeline', content_type=ctype)
    UserObjectPermission.objects.create(
        user=grb_user, object_pk=pipeline.pk,
        permission=perm, content_type=ctype)

    # Point data dir to tmp_path so file writes don't hit real filesystem
    settings.GRACEDB_DATA_DIR = str(tmp_path)

    # POST the fixture file to the create endpoint
    file_path = os.path.join(os.path.dirname(__file__), 'data', filename)
    c = Client()
    c.force_login(grb_user)
    url = reverse('create')

    with open(file_path, 'rb') as f:
        response = c.post(url, {
            'group': 'External',
            'pipeline': pipeline_name,
            'search': 'GRB',
            'eventFile': f,
        })

    assert response.status_code == 302

    # Follow the redirect to the event detail page
    detail_response = c.get(response.url)
    assert detail_response.status_code == 200

    # Verify event fields from the response context
    event = detail_response.context['object']
    no_skymap_info = \
        'gbm_alert' in filename or 'subgrbtargeted_initial' in filename

    assert event.trigger_id is not None
    assert event.gpstime is not None
    if no_skymap_info:
        assert event.ra is None
        assert event.dec is None
    else:
        assert event.ra is not None
        assert event.dec is not None
    if pipeline_name == 'Rubin' or no_skymap_info:
        assert event.error_radius is None
    else:
        assert event.error_radius is not None
