from django.urls import reverse

from core.tests.utils import GraceDbTestBase


class TestManagePasswordView(GraceDbTestBase):
    """Test user access to page for generating basic auth password for API"""

    def test_internal_user_get(self):
        """Internal user *can't* get to manage password page"""
        url = reverse('manage-password')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_get(self):
        """LV-EM user can get to manage password page"""
        url = reverse('manage-password')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_public_user_get(self):
        """Public user can't get to manage password page"""
        url = reverse('manage-password')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
