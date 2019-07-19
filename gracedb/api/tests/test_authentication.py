from base64 import b64encode
try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from api.backends import (
    GraceDbBasicAuthentication, GraceDbX509Authentication,
    GraceDbAuthenticatedAuthentication,
)
from api.tests.utils import GraceDbApiTestBase
from api.utils import api_reverse
from ligoauth.models import X509Cert


# Make sure to test password expiration
class TestGraceDbBasicAuthentication(GraceDbApiTestBase):
    """Test basic auth backend for API in full auth cycle"""

    @classmethod
    def setUpTestData(cls):
        super(TestGraceDbBasicAuthentication, cls).setUpTestData()

        # Set up password for LV-EM user account
        cls.password = 'passw0rd'
        cls.lvem_user.set_password(cls.password)
        cls.lvem_user.save()

    def test_user_authenticate_to_api_with_password(self):
        """User can authenticate to API with correct password"""
        # Set up and make request
        url = api_reverse('api:root')
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
        headers = {
            'HTTP_AUTHORIZATION': 'Basic {0}'.format(user_and_pass),
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertEqual(response.status_code, 200)

        # Make sure user is authenticated properly by checking the
        # renderer context
        req = response.renderer_context['request']
        self.assertEqual(req.user, self.lvem_user)
        self.assertEqual(req.successful_authenticator.__class__,
            GraceDbBasicAuthentication)

    def test_user_authenticate_to_api_with_bad_password(self):
        """User can't authenticate with wrong password"""
        # Set up and make request
        url = api_reverse('api:root')
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password='b4d'
            ).encode()
        ).decode("ascii")
        headers = {
            'HTTP_AUTHORIZATION': 'Basic {0}'.format(user_and_pass),
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertContains(response, 'Invalid username/password',
            status_code=403)

    def test_user_authenticate_to_api_with_expired_password(self):
        """User can't authenticate with expired password"""
        # Set password to be expired
        self.lvem_user.date_joined = timezone.now() - \
            2*settings.PASSWORD_EXPIRATION_TIME
        self.lvem_user.save(update_fields=['date_joined'])

        # Set up and make request
        url = api_reverse('api:root')
        user_and_pass = b64encode(
            "{username}:{password}".format(
                username=self.lvem_user.username,
                password=self.password
            ).encode()
        ).decode("ascii")
        headers = {
            'HTTP_AUTHORIZATION': 'Basic {0}'.format(user_and_pass),
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertContains(response, 'Your password has expired',
            status_code=403)


class TestGraceDbX509Authentication(GraceDbApiTestBase):
    """Test X509 certificate auth backend for API in full auth cycle"""

    def setUp(self):
        super(TestGraceDbX509Authentication, self).setUp()
        # Patch auth classes to make sure the right one is active
        self.auth_patcher = mock.patch(
            'rest_framework.views.APIView.get_authenticators',
            return_value=[GraceDbX509Authentication(),])
        self.auth_patcher.start()

    def tearDown(self):
        super(TestGraceDbX509Authentication, self).tearDown()
        self.auth_patcher.stop()

    @classmethod
    def setUpTestData(cls):
        super(TestGraceDbX509Authentication, cls).setUpTestData()

        # Set up certificate for internal user account
        cls.x509_subject = '/x509_subject'
        cert = X509Cert.objects.create(subject=cls.x509_subject,
            user=cls.internal_user)

    def test_user_authenticate_to_api_with_x509_cert(self):
        """User can authenticate to API with valid X509 certificate"""
        # Set up and make request
        url = api_reverse('api:root')
        headers = {
            GraceDbX509Authentication.subject_dn_header: self.x509_subject,
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertEqual(response.status_code, 200)

        # Make sure user is authenticated properly by checking the
        # renderer context
        req = response.renderer_context['request']
        self.assertEqual(req.user, self.internal_user)
        self.assertEqual(req.successful_authenticator.__class__,
            GraceDbX509Authentication)

    def test_user_authenticate_to_api_with_bad_x509_cert(self):
        """User can't authenticate with invalid X509 certificate subject"""
        # Set up and make request
        url = api_reverse('api:root')
        headers = {
            GraceDbX509Authentication.subject_dn_header: 'bad subject',
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertContains(response, 'Invalid certificate subject',
            status_code=401)

    def test_inactive_user_authenticate(self):
        """Inactive user can't authenticate"""
        # Set internal user to inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Set up and make request
        url = api_reverse('api:root')
        headers = {
            GraceDbX509Authentication.subject_dn_header: self.x509_subject,
        }
        response = self.client.get(url, data=None, **headers)

        # Check response
        self.assertContains(response, 'User inactive or deleted',
            status_code=401)

    def test_authenticate_cert_with_proxy(self):
        """User can authenticate to API with proxied X509 certificate"""
        # Set up request
        #request = self.factory.get(api_reverse('api:root'))
        #request.META[GraceDbX509Authentication.subject_dn_header] = \
        #    '/CN=123' + self.x509_subject
        #request.META[GraceDbX509Authentication.issuer_dn_header] = \
        #    '/CN=123'

        # Authentication attempt
        #user, other = self.backend_instance.authenticate(request)

        # Check authenticated user
        #self.assertEqual(user, self.internal_user)
        # Make sure user is authenticated properly by checking the
        # renderer context
        #req = response.renderer_context['request']
        #self.assertEqual(req.user, self.internal_user)
        #self.assertEqual(req.successful_authenticator.__class__,
        #    GraceDbAuthenticatedAuthentication)


class TestGraceDbAuthenticatedAuthentication(GraceDbApiTestBase):
    """Test "already-authenticated" auth backend for API"""

    def test_user_authenticate_to_api(self):
        """User can authenticate if already authenticated"""
        # Make request to post-login page to set up session
        headers = {
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
        }
        response = self.client.get(reverse('post-login'), data=None, **headers)

        # Now make a request to the API root
        response = self.client.get(api_reverse('api:root'))

        # Make sure user is authenticated properly by checking the
        # renderer context
        req = response.renderer_context['request']
        self.assertEqual(req.user, self.internal_user)
        self.assertEqual(req.successful_authenticator.__class__,
            GraceDbAuthenticatedAuthentication)

    def test_user_not_authenticated_to_api(self):
        """User can't authenticate if not already authenticated"""
        # Make a request to the API root
        response = self.client.get(api_reverse('api:root'))

        # Check response - should be 200 with AnonymousUser
        self.assertEqual(response.status_code, 200)
        # Make sure user is not authenticated
        req = response.renderer_context['request']
        self.assertTrue(req.user.is_anonymous)
        self.assertFalse(req.user.is_authenticated)
        self.assertEqual(req.successful_authenticator, None)

