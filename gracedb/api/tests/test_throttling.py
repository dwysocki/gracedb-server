from copy import deepcopy

from django.conf import settings
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase


# Copy REST_FRAMEWORK settings dict and override here
drf_settings = settings.REST_FRAMEWORK.copy()
drf_settings['DEFAULT_THROTTLE_RATES']['anon_burst'] = '1/hour'


class TestThrottling(GraceDbApiTestBase):
    """Test API throttles"""

    def tearDown(self):
        super(TestThrottling, self).tearDown()

        # Clear throttle cache
        caches['throttles'].clear()

    @override_settings(REST_FRAMEWORK=drf_settings)
    def test_anon_burst_throttle(self):
        """Test anonymous user burst throttle"""
        url = reverse('api:default:root')

        # First request should be OK
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

        # Second response should get throttled
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 429)
        self.assertIn('Request was throttled', response.content)
