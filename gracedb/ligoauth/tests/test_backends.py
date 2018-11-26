from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup, User, AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings, modify_settings
from django.urls import reverse

from ligoauth.backends import ShibbolethRemoteUserBackend

# See this test class for information about what groups and users
# are already defined for use.
from core.tests.utils import GraceDbTestBase


class TestShibbolethRemoteUserBackend(GraceDbTestBase):
    """Test backend for authenticating users with a Shibboleth session"""

    @classmethod
    def setUpClass(cls):
        super(TestShibbolethRemoteUserBackend, cls).setUpClass()

        # Requests will be for / by default
        cls.url = reverse('home')

        # Attach request factory to class
        cls.factory= RequestFactory()

        # Set up backend instance
        cls.backend_instance = ShibbolethRemoteUserBackend()

    def test_user_authenticate(self):
        """Backend authenticates internal user properly"""
        request = self.factory.get(self.url)
        user = self.backend_instance.authenticate(request,
            remote_user=self.internal_user.username)
        self.assertEqual(user, self.internal_user)

    def test_user_creation(self):
        """Backend creates new user properly"""
        # New user information
        user_data = {
            'first_name': 'new',
            'last_name': 'user',
            'email': 'new.user@site.com',
            'username': 'new.user',
        }
        # Set up request and headers
        request = self.factory.get(self.url)
        for k,v in user_data.items():
            if settings.SHIB_ATTRIBUTE_MAP.has_key(k):
                request.META[settings.SHIB_ATTRIBUTE_MAP[k]] = v

        # Pass data to backend
        user = self.backend_instance.authenticate(request,
            remote_user=user_data['username'])

        # Check results
        self.assertTrue(user is not None)
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.username, user_data['username'])
        self.assertEqual(user.first_name, user_data['first_name'])
        self.assertEqual(user.last_name, user_data['last_name'])
        self.assertEqual(user.email, user_data['email'])

    def test_user_update(self):
        # Updated user information
        new_user_data = {
            'email': 'new_email@site.com',
        }
        # Set up request and headers
        request = self.factory.get(self.url)
        for k,v in new_user_data.items():
            if settings.SHIB_ATTRIBUTE_MAP.has_key(k):
                request.META[settings.SHIB_ATTRIBUTE_MAP[k]] = v

        # Get initial user data
        initial_user_data = {k: getattr(self.internal_user, k)
            for k in ['first_name', 'last_name', 'email', 'username']}

        # Pass data to backend
        user = self.backend_instance.authenticate(request,
            remote_user=self.internal_user.username)

        # Check results
        self.assertEqual(user, self.internal_user)
        self.assertEqual(user.username, initial_user_data['username'])
        self.assertEqual(user.first_name, initial_user_data['first_name'])
        self.assertEqual(user.last_name, initial_user_data['last_name'])
        self.assertEqual(user.email, new_user_data['email'])

    def test_inactive_user_authenticate(self):
        """Inactive user can't authenticate"""
        # Set user to inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Set up request and process with backend
        request = self.factory.get(self.url)
        user = self.backend_instance.authenticate(request,
            remote_user=self.internal_user.username)

        # Check result - should be None
        self.assertTrue(user is None)
