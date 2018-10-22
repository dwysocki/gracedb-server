from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.urls import resolve

from rest_framework.authentication import BaseAuthentication, \
    BasicAuthentication, get_authorization_header
from rest_framework import exceptions

from ligoauth.models import X509Cert
from .utils import is_api_request

import re
import logging
logger = logging.getLogger(__name__)


class GraceDbBasicAuthentication(BasicAuthentication):
    api_only = False

    def authenticate(self, request, *args, **kwargs):
        """
        Same as base class, except we require the request to be directed
        toward the basic auth API.
        """
        logger.debug("{0}: beginning auth attempt".format(self.__class__.__name__))

        # Make sure this request is directed to the basic auth API
        if self.api_only and not is_api_request(request.path, 'basic'):
            logger.debug("{0}: request not directed to basic auth API".format(self.__class__.__name__))
            return None

        # Call base class authenticate() method
        return super(GraceDbBasicAuthentication, self).authenticate(request,
            *args, **kwargs)

    def authenticate_credentials(self, userid, password):
        """
        Mostly copied from rest_framework.authentication.BasicAuthentication,
        but we needed to add the hacky password expiration check at the end.
        """
        credentials = {
            get_user_model().USERNAME_FIELD: userid,
            'password': password
        }
        logger.debug("{0}: attempting to authenticate {1}".format(self.__class__.__name__, userid))
        user = authenticate(**credentials)
        if user:
            logger.debug("{0}: user {1} authenticated".format(self.__class__.__name__, userid))

        if user is None:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        # Check password expiration
        # NOTE: This is super hacky because we are using date_joined to store
        # the date when the password was set. See managePassword() in 
        # userprofile.views.
        password_expiry = user.date_joined + settings.PASSWORD_EXPIRATION_TIME
        if timezone.now() > password_expiry:
            msg = ('Your password has expired. Please log in to the web '
                'interface and request another.')
            raise exceptions.AuthenticationFailed(_(msg))

        return (user, None)


class GraceDbX509Authentication(BaseAuthentication):
    www_authenticate_realm = 'api'
    api_only = False
    subject_dn_header = getattr(settings, 'X509_SUBJECT_DN_HEADER',
        'SSL_CLIENT_S_DN')
    issuer_dn_header = getattr(settings, 'X509_ISSUER_DN_HEADER',
        'SSL_CLIENT_I_DN')
    proxy_pattern = re.compile(r'^(.*?)(/CN=\d+)*$')

    def authenticate(self, request):
        logger.debug("{0}: beginning auth attempt".format(self.__class__.__name__))

        # Make sure this request is directed to the basic auth API
        if self.api_only and not is_api_request(request.path, 'x509'):
            logger.debug("{0}: request not directed to x509 API".format(self.__class__.__name__))
            return None

        # Try to get credentials from request headers
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
        issuer = request.META.get(cls.issuer_dn_header, None)

        # Proxies can be signed by proxies; each level adds '/CN=[0-9]+' to the
        # signers' subject, so we remove those to get the original identity's
        # certificate DN
        if certdn and certdn.startswith(issuer):
            certdn = self.proxy_pattern.match(issuer).group(1)

        return certdn

    def authenticate_credentials(self, user_cert_dn):
        """
        Mostly copied from rest_framework.authentication.BasicAuthentication,
        but we needed to add the hacky password expiration check at the end.
        """
        logger.debug("{0}: attempting to authenticate {1}".format(self.__class__.__name__, user_cert_dn))

        cert = X509Cert.objects.get(subject=user_cert_dn)
        num_users = cert.users.count()

        if (num_users > 1):
            raise exceptions.AuthenticationFailed(_('Multiple users have the '
                'same certificate subject'))
        elif (num_users == 0):
            raise exceptions.AuthenticationFailed(_('No user found for this '
                'certificate'))

        user = cert.users.first()
        if user:
            logger.debug("{0}: user {1} authenticated".format(self.__class__.__name__, user.username))

        return (user, None)


class GraceDbShibAuthentication(BaseAuthentication):
    """
    If user is already authenticated by the main Django middleware,
    don't make them authenticate again.

    This is only used for the web-based API.
    """
    def authenticate(self, request):
        logger.debug("{0}: beginning auth attempt".format(self.__class__.__name__))
        if (request._request.user.is_authenticated and
            is_api_request(request.path, 'shib')):

            logger.debug("{0}: user {1} already authenticated".format(self.__class__.__name__, request._request.user.username))
            return (request._request.user, None)
        else:
            return None
