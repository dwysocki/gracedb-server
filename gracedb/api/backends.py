import base64
import logging
import OpenSSL.crypto
import OpenSSL.SSL
import re

from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.http import unquote, unquote_plus
from django.utils.translation import gettext_lazy as _
from django.urls import resolve

from rest_framework import authentication, exceptions

from ligoauth.models import X509Cert
from .utils import is_api_request

import scitokens
from jwt import InvalidTokenError
from scitokens.utils.errors import SciTokensException

# Set up logger
logger = logging.getLogger(__name__)


class GraceDbBasicAuthentication(authentication.BasicAuthentication):
    allow_ajax = False
    api_only = True

    def authenticate(self, request, *args, **kwargs):
        """
        Same as base class, except we require the request to be directed
        toward the basic auth API.
        """
        # Make sure this request is directed to the API
        if self.api_only and not is_api_request(request.path):
            return None

        # Don't allow this auth type for AJAX requests, since we don't want it
        # to work for API requests made by the web views.
        #if request.is_ajax() and not self.allow_ajax:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and not self.allow_ajax:
            return None

        # Call base class authenticate() method
        return super(GraceDbBasicAuthentication, self).authenticate(request)

    def authenticate_credentials(self, userid, password, request=None):
        """
        Add a hacky password expiration check to the inherited method.
        """
        user_auth_tuple = super(GraceDbBasicAuthentication, self) \
            .authenticate_credentials(userid, password, request)
        user = user_auth_tuple[0]

        # Check password expiration
        # NOTE: This is *super* hacky because we are using date_joined to store
        # the date when the password was set. See managePassword() in 
        # userprofile.views.
        password_expiry = user.date_joined + settings.PASSWORD_EXPIRATION_TIME
        if timezone.now() > password_expiry:
            msg = ('Your password has expired. Please log in to the web '
                'interface and request another.')
            raise exceptions.AuthenticationFailed(_(msg))

        return user_auth_tuple


class GraceDbSciTokenAuthentication(authentication.BasicAuthentication):

    class MultiIssuerEnforcer(scitokens.Enforcer):
        def __init__(self, issuer, **kwargs):
            if not isinstance(issuer, (tuple, list)):
                issuer = [issuer]
            super().__init__(issuer, **kwargs)

        def _validate_iss(self, value):
            return value in self._issuer


    def authenticate(self, request, public_key=None):
        # Get token from header
        try:
            bearer = request.headers["Authorization"]
        except KeyError:
            return None
        auth_type, serialized_token = bearer.split()
        if  auth_type != "Bearer":
            return None

        # Deserialize token
        try:
            token = scitokens.SciToken.deserialize(
                serialized_token,
                # deserialize all tokens, enforce audience later
                audience={"ANY"} | set(settings.SCITOKEN_AUDIENCE),
                public_key=public_key,
            )
        except (InvalidTokenError, SciTokensException) as exc:
            return None

        # Enforce scitoken logic
        enforcer = self.MultiIssuerEnforcer(
            settings.SCITOKEN_ISSUER,
            audience = settings.SCITOKEN_AUDIENCE,
        )

        try:
            authz, path = settings.SCITOKEN_SCOPE.split(":", 1)
        except ValueError:
            authz = settings.SCITOKEN_SCOPE
            path = None
        if not enforcer.test(token, authz, path):
            return None

        # Get username from token 'Subject' claim.
        try:
            user = User.objects.get(username=token['sub'].lower())
        except User.DoesNotExist:
            return None

        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                _('User inactive or deleted'))

        return (user, None)


class GraceDbX509Authentication(authentication.BaseAuthentication):
    """
    Authentication based on X509 certificate subject.
    Certificate should be verified by Apache already.
    """
    allow_ajax = False
    api_only = True
    www_authenticate_realm = 'api'
    subject_dn_header = getattr(settings, 'X509_SUBJECT_DN_HEADER',
        'SSL_CLIENT_S_DN')
    issuer_dn_header = getattr(settings, 'X509_ISSUER_DN_HEADER',
        'SSL_CLIENT_I_DN')
    proxy_pattern = re.compile(r'^(.*?)(/CN=\d+)*$')

    def authenticate(self, request):
        # Make sure this request is directed to the API
        if self.api_only and not is_api_request(request.path):
            return None

        # Don't allow this auth type for AJAX requests - this is because
        # users with certificates in their browser can still authenticate via
        # this mechanism in the web view (since it makes API queries), even
        # when they are not logged in.
        #if request.is_ajax() and not self.allow_ajax:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and not self.allow_ajax:
            return None

        # Try to get credentials from request headers.
        user_cert_dn = self.get_cert_dn_from_request(request)

        # If no user dn is found, pass on to the next auth method
        if not user_cert_dn:
            return None

        return self.authenticate_credentials(user_cert_dn)

    @classmethod
    def authenticate_header(cls, request):
        return 'X509 realm="{0}"'.format(cls.www_authenticate_realm)

    @classmethod
    def get_cert_dn_from_request(cls, request):
        """Get SSL headers and return DN for user"""

        # Get subject and issuer DN from SSL headers
        certdn = request.META.get(cls.subject_dn_header, None)
        issuer = request.META.get(cls.issuer_dn_header, '')

        # Handled proxied certificates
        certdn = cls.extract_subject_from_proxied_cert(certdn, issuer)

        return certdn

    @classmethod
    def extract_subject_from_proxied_cert(cls, subject, issuer):
        """
        Handles the case of "impersonation proxies", where /CN=[0-9]+ is
        appended to the end of the certificate subject. This occurs when you
        generate a certificate and it "follows" you to another machine - you
        effectively self-sign a copy of the certificate to use on the other
        machine.

        Example:

        Albert generates a certificate with ligo-proxy-init on his laptop.

        Subject and issuer when he pings the GraceDB server from his laptop:
        /DC=org/DC=cilogon/C=US/O=LIGO/CN=Albert Einstein albert.einstein@ligo.org
        /DC=org/DC=cilogon/C=US/O=CILogon/CN=CILogon Basic CA 1

        Subject and issuer when he gsisshs to an LDG cluster and then pings the
        GraceDB server from there:
        /DC=org/DC=cilogon/C=US/O=LIGO/CN=Albert Einstein albert.einstein@ligo.org/CN=1492637212
        /DC=org/DC=cilogon/C=US/O=LIGO/CN=Albert Einstein albert.einstein@ligo.org

        If he then gsisshs to *another* machine from there and repeats this,
        he would get:
        /DC=org/DC=cilogon/C=US/O=LIGO/CN=Albert Einstein albert.einstein@ligo.org/CN=1492637212/CN=28732493
        /DC=org/DC=cilogon/C=US/O=LIGO/CN=Albert Einstein albert.einstein@ligo.org/CN=1492637212
        """
        if subject and issuer and subject.startswith(issuer):
            # If we get here, we have an impersonation proxy, so we extract
            # the proxy /CN=12345... part from the subject.  Could also
            # do it from the issuer (see above examples)
            subject = cls.proxy_pattern.match(subject).group(1)

        return subject

    def authenticate_credentials(self, user_cert_dn):
        certs = X509Cert.objects.filter(subject=user_cert_dn)
        if not certs.exists():
            raise exceptions.AuthenticationFailed(_('Invalid certificate '
                'subject'))
        cert = certs.first()

        # Check if user is active
        user = cert.user
        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                _('User inactive or deleted'))

        return (user, None)


class GraceDbX509CertInfosAuthentication(GraceDbX509Authentication):
    """
    Authentication based on X509 "infos" header.
    Certificate should be verified by Traefik already.
    """
    allow_ajax = False
    api_only = True
    infos_header = getattr(settings, 'X509_INFOS_HEADER',
        'HTTP_X_FORWARDED_TLS_CLIENT_CERT_INFOS')
    infos_pattern = re.compile(r'Subject="(.*?)".*Issuer="(.*?)"')

    @classmethod
    def get_cert_dn_from_request(cls, request):
        """Get SSL headers and return subject for user"""

        # Get infos from request headers
        infos = request.META.get(cls.infos_header, None)

        # Unquote (handle pluses -> spaces)
        infos_unquoted = unquote_plus(infos)

        # Extract subject and issuer
        subject, issuer = cls.infos_pattern.search(infos_unquoted).groups()

        # Convert formats
        subject = cls.convert_format(subject)
        issuer = cls.convert_format(issuer)

        # Handled proxied certificates
        subject = cls.extract_subject_from_proxied_cert(subject, issuer)

        return subject

    @staticmethod
    def convert_format(s):
        # Convert subject or issuer strings from comma to slash format
        s = s.replace(',', '/')
        if not s.startswith('/'):
            s = '/' + s
        return s


class GraceDbX509FullCertAuthentication(GraceDbX509Authentication):
    """
    Authentication based on a full X509 certificate. We verify the
    certificate here.
    """
    allow_ajax = False
    api_only = True
    www_authenticate_realm = 'api'
    cert_header = getattr(settings, 'X509_CERT_HEADER',
        'HTTP_X_FORWARDED_TLS_CLIENT_CERT')

    def authenticate(self, request):

        # Make sure this request is directed to the API
        if self.api_only and not is_api_request(request.path):
            return None

        # Don't allow this auth type for AJAX requests - this is because
        # users with certificates in their browser can still authenticate via
        # this mechanism in the web view (since it makes API queries), even
        # when they are not logged in.
        #if request.is_ajax() and not self.allow_ajax:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and not self.allow_ajax:
            return None

        # Try to get certificate from request headers
        cert_data = self.get_certificate_data_from_request(request)

        # If no certificate is found, abort
        if not cert_data:
            return None

        # Verify certificate
        try:
            certificate = self.verify_certificate_chain(cert_data)
        except exceptions.AuthenticationFailed as e:
            raise
        except Exception as e:
            raise exceptions.AuthenticationFailed(_('Certificate could not be '
                'verified'))

        return self.authenticate_credentials(certificate)

    @classmethod
    def get_certificate_data_from_request(cls, request):
        """Get certificate data from request"""
        cert_quoted = request.META.get(cls.cert_header, None)
        if cert_quoted is None:
            return None

        # Process the certificate a bit
        cert_b64 = unquote(cert_quoted)
        cert_der = base64.b64decode(cert_b64)

        return cert_der

    def verify_certificate_chain(self, cert_data, capath=settings.CAPATH):
        # Load certificate data
        certificate = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_ASN1, cert_data)

        # Set up context and get certificate store 
        ctx = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
        ctx.load_verify_locations(None, capath=capath)
        store = ctx.get_cert_store()

        # Verify certificate
        store_ctx = OpenSSL.crypto.X509StoreContext(store, certificate)
        store_ctx.verify_certificate()

        # Check if expired
        if certificate.has_expired():
            raise exceptions.AuthenticationFailed(_('Certificate has expired'))

        return certificate

    def authenticate_credentials(self, certificate):
        # Get subject and issuer
        subject = self.get_certificate_subject_string(certificate)
        issuer = self.get_certificate_issuer_string(certificate)

        # Handled proxied certificates
        subject = self.extract_subject_from_proxied_cert(subject, issuer)

        # Authenticate credentials
        return super(GraceDbX509FullCertAuthentication, self) \
            .authenticate_credentials(subject)

    @staticmethod
    def get_certificate_subject_string(certificate):
        subject = certificate.get_subject()
        subject_decoded = [[word.decode("utf8") for word in sets]
                for sets in subject.get_components()]
        subject_string = '/' + "/".join(["=".join(c) for c in
            subject_decoded])
        return subject_string

    @staticmethod
    def get_certificate_issuer_string(certificate):
        issuer = certificate.get_issuer()
        issuer_decoded = [[word.decode("utf8") for word in sets]
                for sets in issuer.get_components()]
        issuer_string = '/' + "/".join(["=".join(c) for c in
            issuer_decoded])
        return issuer_string


class GraceDbAuthenticatedAuthentication(authentication.BaseAuthentication):
    """
    If user is already authenticated by the main Django middleware,
    don't make them authenticate again.

    This is mostly (only?) used for access to the web-browsable API when
    the user is already authenticated via Shibboleth.
    """
    api_only = True

    def authenticate(self, request):

        # Make sure this request is directed to the API
        if self.api_only and not is_api_request(request.path):
            return None

        if (hasattr(request, '_request') and hasattr(request._request, 'user')
            and hasattr(request._request.user, 'is_authenticated') and
            request._request.user.is_authenticated):
            return (request._request.user, None)
        else:
            return None
