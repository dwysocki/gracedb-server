try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from django.conf import settings
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase


class TestThrottling(GraceDbApiTestBase):
    """Test API throttles"""

    @mock.patch('api.throttling.BurstAnonRateThrottle.get_rate',
        return_value='1/hour'
    )
    def test_anon_burst_throttle(self, mock_get_rate):
        """Test anonymous user burst throttle"""
        url = reverse('api:default:root')

        # First request should be OK
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

        # Second response should get throttled
        response = self.request_as_user(url, "GET")
        self.assertContains(response, 'Request was throttled', status_code=429)
        self.assertIn('Retry-After', response.headers)
