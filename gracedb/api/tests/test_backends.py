from base64 import b64encode

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.urls import reverse
from django.utils import timezone

from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from user_sessions.middleware import SessionMiddleware

from api.backends import (
    GraceDbBasicAuthentication, GraceDbX509Authentication,
    GraceDbSciTokenAuthentication, GraceDbAuthenticatedAuthentication,
)
from api.tests.utils import GraceDbApiTestBase
from api.utils import api_reverse
from ligoauth.middleware import ShibbolethWebAuthMiddleware
from ligoauth.models import X509Cert

import scitokens
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from core.tests.utils import GraceDbTestBase
from django.test import override_settings


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
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        self.assertEqual(user, self.lvem_user)

    def test_user_authenticate_to_api_with_bad_password(self):
        """User can't authenticate with wrong password"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password='b4d'
            ).encode()
        ).decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)

    def test_user_authenticate_to_api_with_expired_password(self):
        """User can't authenticate with expired password"""
        # Set user's password date (date_joined) so that it is expired
        self.lvem_user.date_joined = timezone.now() - \
            2*settings.PASSWORD_EXPIRATION_TIME
        self.lvem_user.save(update_fields=['date_joined'])

        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt should fail
        with self.assertRaisesRegex(exceptions.AuthenticationFailed,
            'Your password has expired'):
            user, other = self.backend_instance.authenticate(request)

    def test_user_authenticate_non_api(self):
        """User can't authenticate to a non-API URL path"""
        # Set up request
        request = self.factory.get(reverse('home'))
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
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
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
        request.META['HTTP_AUTHORIZATION'] = 'Basic {0}'.format(user_and_pass)

        # Authentication attempt should fail
        with self.assertRaises(exceptions.AuthenticationFailed):
            user, other = self.backend_instance.authenticate(request)


class TestGraceDbSciTokenAuthentication(GraceDbTestBase):
    """Test SciToken auth backend for API"""

    TEST_ISSUER = "local"
    TEST_AUDIENCE = ["TEST"]
    TEST_SCOPE = "read:/GraceDB"

    @classmethod
    def setUpClass(cls):
        super(TestGraceDbSciTokenAuthentication, cls).setUpClass()

        # Attach request factory to class
        cls.backend_instance = GraceDbSciTokenAuthentication()
        cls.factory = APIRequestFactory()

    @classmethod
    def setUpTestData(cls):
        super(TestGraceDbSciTokenAuthentication, cls).setUpTestData()

    def setUp(self):
        self._private_key = generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
        self._public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        keycache = scitokens.utils.keycache.KeyCache.getinstance()
        keycache.addkeyinfo("local", "sample_key", self._private_key.public_key())
        now = int(time.time())
        self._token = scitokens.SciToken(key = self._private_key, key_id="sample_key")
        self._token.update_claims({
        "iat": now,
        "nbf": now,
        "exp": now + 86400,
        "iss": self.TEST_ISSUER,
        "aud": self.TEST_AUDIENCE,
        "scope": self.TEST_SCOPE,
        "sub": str(self.internal_user),
        })
        self._serialized_token = self._token.serialize(issuer = "local")
        self._no_kid_token = scitokens.SciToken(key = self._private_key)

    # test test_function
    def test_create(self):
        """
        Test the creation of a simple SciToken.
        """

        token = scitokens.SciToken(key = self._private_key)
        token.update_claims({"test": "true"})
        serialized_token = token.serialize(issuer = "local")

        self.assertEqual(len(serialized_token.decode('utf8').split(".")), 3)
        print(serialized_token)

    @override_settings(
        SCITOKEN_ISSUER="local",
        SCITOKEN_AUDIENCE=["TEST"],
    )
    def test_user_authenticate_to_api_with_scitoken(self):
        """User can authenticate to API with valid Scitoken"""
        # Set up request
        request = self.factory.get(api_reverse('api:root'))

        token_str = 'Bearer ' + self._serialized_token.decode()
        request.headers = {'Authorization': token_str}

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request, public_key=self._public_pem)

        # Check authenticated user
        self.assertEqual(user, self.internal_user)

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
        cert = X509Cert.objects.create(subject=cls.x509_subject,
            user=cls.internal_user)

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
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            self.x509_subject + '/CN=123456789'
        request.META[GraceDbX509Authentication.issuer_dn_header] = \
            self.x509_subject

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        self.assertEqual(user, self.internal_user)

    def test_authenticate_cert_with_double_proxy(self):
        """User can authenticate to API with double-proxied X509 certificate"""
        proxied_x509_subject = self.x509_subject + '/CN=123456789'

        # Set up request
        request = self.factory.get(api_reverse('api:root'))
        request.META[GraceDbX509Authentication.subject_dn_header] = \
            proxied_x509_subject + '/CN=987654321'
        request.META[GraceDbX509Authentication.issuer_dn_header] = \
            proxied_x509_subject

        # Authentication attempt
        user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        self.assertEqual(user, self.internal_user)

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
