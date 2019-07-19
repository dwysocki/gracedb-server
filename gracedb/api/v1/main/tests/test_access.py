from __future__ import absolute_import

from django.conf import settings
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


class TestPublicAccess(GraceDbApiTestBase):

    def test_api_root(self):
        """Unauthenticated user can access API root"""
        url = v_reverse('root')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

    def test_tag_list(self):
        """Unauthenticated user can access tag list"""
        url = v_reverse('tag-list')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

    def test_public_user_performance_info(self):
        """Unauthenticated user can't access performance info"""
        url = v_reverse('performance-info')
        response = self.request_as_user(url, "GET")
        self.assertContains(
            response,
            'Authentication credentials were not provided',
            status_code=403
        )

    def test_lvem_user_performance_info(self):
        """LV-EM user can't access performance info"""
        url = v_reverse('performance-info')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertContains(
            response,
            'Forbidden',
            status_code=403
        )
