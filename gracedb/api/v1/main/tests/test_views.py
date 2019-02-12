from __future__ import absolute_import

from django.conf import settings
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


class TestUserInfoView(GraceDbApiTestBase):

    def test_internal_user(self):
        """Internal user sees correct information"""
        url = v_reverse('user-info')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Test information
        self.assertEqual(response.data['is_internal_user'], True)
        for attr in ['username', 'first_name', 'last_name', 'email']:
            self.assertEqual(response.data.get(attr),
                getattr(self.internal_user, attr))

    def test_lvem_user(self):
        """LV-EM user sees correct information"""
        url = v_reverse('user-info')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

        # Test information
        self.assertEqual(response.data['is_internal_user'], False)
        for attr in ['username', 'first_name', 'last_name', 'email']:
            self.assertEqual(response.data.get(attr),
                getattr(self.lvem_user, attr))

    def test_public_user(self):
        """Public user sees correct information"""
        url = v_reverse('user-info')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

        # Test information
        self.assertEqual(response.data.keys(), ['username'])
        self.assertEqual(response.data['username'], 'AnonymousUser')
