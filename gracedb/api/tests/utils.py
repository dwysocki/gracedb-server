from copy import deepcopy
import mock

from django.conf import settings
from django.core.cache import caches
from django.test import override_settings

from rest_framework.test import APIClient

from core.tests.utils import GraceDbTestBase


def fix_settings(key, value):
    """
    Dynamically override settings for testing. But, it will only
    ever be useful if rest_framework fixes the way that their
    settings work so that override_settings actually works.

    'key' should be x.y.z for nested dictionaries.
    """
    api_settings = deepcopy(settings.REST_FRAMEWORK)

    key_list = key.split('.')
    new_dict = reduce(dict.get, key_list[:-1], api_settings)
    new_dict[key_list[-1]] = value

    return api_settings


@override_settings(
    ALLOW_BLANK_USER_AGENT_TO_API=True,
)
class GraceDbApiTestBase(GraceDbTestBase):
    client_class = APIClient

    def setUp(self):
        super(GraceDbApiTestBase, self).setUp()
        # Patch throttle and start patcher
        self.patcher = mock.patch('api.throttling.BurstAnonRateThrottle.get_rate',
            return_value='1000/second')
        self.patcher.start()


    def tearDown(self):
        super(GraceDbApiTestBase, self).tearDown()

        # Clear throttle cache
        caches['throttles'].clear()

        # Stop patcher
        self.patcher.stop()
