# Test that querysets are filtered properly based on
# permissions so that users only see what they should
from __future__ import absolute_import
import datetime
import ipdb

from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from guardian.shortcuts import assign_perm, remove_perm

from api.tests.utils import GraceDbApiTestBase
from core.permissions import expose_log_to_lvem, expose_log_to_public
from core.tests.utils import GraceDbTestBase, \
    SupereventManagersGroupAndUserSetup, AccessManagersGroupAndUserSetup, \
    SignoffGroupsAndUsersSetup
from events.models import Label, Tag, EMGroup
from superevents.models import Superevent, Labelling, Log, VOEvent, \
    EMObservation, Signoff
from superevents.tests.mixins import SupereventCreateMixin, SupereventSetup
from superevents.utils import create_log
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


class TestSupereventSerializerViaWeb(SupereventSetup, GraceDbApiTestBase):
    """
    Test superevent serialization via full view to ensure that
    contents are handled as expected for authenticated versus
    unauthenticated users
    """

    def test_internal_user_get_superevent_detail(self):
        """Internal user sees events link and all event graceids"""
        # Set up URL
        url = v_reverse('superevents:superevent-detail',
            args=[self.public_superevent.superevent_id])
        # Get response and check code
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)
        # Check data on page
        response_keys = list(response.json())
        response_links = response.json()['links']
        self.assertIn('preferred_event', response_keys)
        self.assertIn('gw_events', response_keys)
        self.assertIn('em_events', response_keys)
        self.assertIn('pipeline_preferred_events', response_keys)
        self.assertIn('events', response_links)

    def test_lvem_user_get_superevent_detail(self):
        """LV-EM user sees events link and all event graceids"""
        # Set up URL
        url = v_reverse('superevents:superevent-detail',
            args=[self.public_superevent.superevent_id])
        # Get response and check code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        # Check data on page
        response_keys = list(response.json())
        response_links = response.json()['links']
        self.assertIn('preferred_event', response_keys)
        self.assertIn('gw_events', response_keys)
        self.assertIn('em_events', response_keys)
        self.assertIn('events', response_links)

    def test_public_user_get_superevent_detail(self):
        """Public user does not see events link or all event graceids"""
        # Set up URL
        url = v_reverse('superevents:superevent-detail',
            args=[self.public_superevent.superevent_id])
        # Get response and check code
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)
        # Check data on page
        response_keys = list(response.json())
        response_links = response.json()['links']
        self.assertNotIn('preferred_event', response_keys)
        self.assertNotIn('gw_events', response_keys)
        self.assertNotIn('em_events', response_keys)
        self.assertNotIn('pipeline_preferred_events', response_keys)
        self.assertNotIn('events', response_links)
