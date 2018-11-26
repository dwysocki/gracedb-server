from base64 import b64encode

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.urls import reverse

from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from user_sessions.middleware import SessionMiddleware

from api.backends import (
    GraceDbBasicAuthentication, GraceDbX509Authentication,
    GraceDbAuthenticatedAuthentication,
)
from api.tests.utils import GraceDbApiTestBase
from api.utils import api_reverse
from ligoauth.middleware import ShibbolethWebAuthMiddleware
from ligoauth.models import X509Cert


# Make sure to test password expiration
class TestGraceDbBasicAuthentication(GraceDbApiTestBase):
    """Test basic auth backend for API"""

    @classmethod
    def setUpClass(cls):
        super(TestGraceDbBasicAuthentication, cls).setUpClass()

        # Attach request factory to class
        cls.backend_instance = GraceDbBasicAuthentication()
        cls.factory = APIRequestFactory()

    @classmethod
    def setUpTestData(cls):
        super(TestGraceDbBasicAuthentication, cls).setUpTestData()

        # Set up password for LV-EM user account
        cls.password = 'passw0rd'
        cls.lvem_user.set_password(cls.password)
        cls.lvem_user.save()

    def test_user_authenticate_to_api_with_password(self):
        """User can authenticate to API with correct password"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        user_and_pass = b64encode(b"{username}:{password}".format(
            username=self.lvem_user.username, password=self.password)) \
            .decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        self.assertEqual(user, self.lvem_user)

    def test_user_authenticate_to_api_with_bad_password(self):
        """User can't authenticate with wrong password"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        user_and_pass = b64encode(b"{username}:{password}".format(
            username=self.lvem_user.username, password='b4d')).decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)

    def test_user_authenticate_non_api(self):
        """User can't authenticate to a non-API URL path"""
        # Set up request
        request = self.factory.get(reverse('home'))
        user_and_pass = b64encode(b"{username}:{password}".format(
            username=self.lvem_user.username, password=self.password)) \
            .decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Try to authenticate
        user_auth_tuple = self.backend_instance.authenticate(request)
        self.assertEqual(user_auth_tuple, None)

    def test_inactive_user_authenticate(self):
        """Inactive user can't authenticate"""
        # Set LV-EM user to inactive
        self.lvem_user.is_active = False
        self.lvem_user.save(update_fields=['is_active'])

        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        user_and_pass = b64encode(b"{username}:{password}".format(
            username=self.lvem_user.username, password=self.password)) \
            .decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)


class TestGraceDbX509Authentication(GraceDbApiTestBase):
    """Test X509 certificate auth backend for API"""

    @classmethod
    def setUpClass(cls):
        super(TestGraceDbX509Authentication, cls).setUpClass()

        # Attach request factory to class
        cls.backend_instance = GraceDbX509Authentication()
        cls.factory = APIRequestFactory()

    @classmethod
    def setUpTestData(cls):
        super(TestGraceDbX509Authentication, cls).setUpTestData()

        # Set up certificate for internal user account
        cls.x509_subject = '/x509_subject'
        cert = X509Cert.objects.create(subject=cls.x509_subject)
        cert.users.add(cls.internal_user)

    def test_user_authenticate_to_api_with_x509_cert(self):
        """User can authenticate to API with valid X509 certificate"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            self.x509_subject

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        self.assertEqual(user, self.internal_user)

    def test_user_authenticate_to_api_with_bad_x509_cert(self):
        """User can't authenticate with invalid X509 certificate subject"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            'bad subject'

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)

    def test_user_authenticate_non_api(self):
        """User can't authenticate to a non-API URL path"""
        # Set up request
        request = self.factory.get(reverse('home'))
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            self.x509_subject

        # Try to authenticate
        user_auth_tuple = self.backend_instance.authenticate(request)
        self.assertEqual(user_auth_tuple, None)

    def test_inactive_user_authenticate(self):
        """Inactive user can't authenticate"""
        # Set internal user to inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            self.x509_subject

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)

    def test_authenticate_cert_with_proxy(self):
        """User can authenticate to API with proxied X509 certificate"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        #request.META[GraceDbX509Authentication.subject_dn_header] = \
        #    '/CN=123' + self.x509_subject
        #request.META[GraceDbX509Authentication.issuer_dn_header] = \
        #    '/CN=123'

        # Authentication attempt
        #user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        #self.assertEqual(user, self.internal_user)


class TestGraceDbAuthenticatedAuthentication(GraceDbApiTestBase):
    """Test shibboleth auth backend for API"""

    @classmethod
    def setUpClass(cls):
        super(TestGraceDbAuthenticatedAuthentication, cls).setUpClass()

        # Attach request factory to class
        cls.backend_instance = GraceDbAuthenticatedAuthentication()
        cls.factory = APIRequestFactory()

    def test_user_authenticate_to_api(self):
        """User can authenticate if already authenticated"""
        # Need to convert request to a rest_framework Request,
        # as would be done in a view's initialize_request() method.
        request = self.factory.get(api_reverse('api:root'))
        request.user = self.internal_user
        request = Request(request=request)

        # Try to authenticate user
        user, other = self.backend_instance.authenticate(request)
        self.assertEqual(user, self.internal_user)

    def test_user_not_authenticated_to_api(self):
        """User can't authenticate if not already authenticated"""
        # Need to convert request to a rest_framework Request,
        # as would be done in a view's initialize_request() method.
        request = self.factory.get(api_reverse('api:root'))
        # Preprocessing to set request.user to anonymous
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        request = Request(request=request)

        # Try to authenticate user
        user_auth_tuple = self.backend_instance.authenticate(request)
        self.assertEqual(user_auth_tuple, None)

    def test_user_authenticate_to_non_api(self):
        """User can't authenticate to non-API URL path"""
        # Need to convert request to a rest_framework Request,
        # as would be done in a view's initialize_request() method.
        request = self.factory.get(reverse('home'))
        request = Request(request=request)

        # Try to authenticate user
        user_auth_tuple = self.backend_instance.authenticate(request)
        self.assertEqual(user_auth_tuple, None)
