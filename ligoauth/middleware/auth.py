
import re
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.backends import RemoteUserBackend as DefaultRemoteUserBackend
from ligoauth.models import certdn_to_user

from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponseForbidden

proxyPattern = re.compile(r'^(.*?)(/CN=\d+)*$')

def cert_dn_from_request(request):
    """Take a request, rummage through SSL_* headers, return the DN for the user."""
    certdn = request.META.get('SSL_CLIENT_S_DN')
    issuer = request.META.get('SSL_CLIENT_I_DN')

    if not certdn:
        try:
            # mod_python is a little off...
            # SSL info is in request._req
            # Need to try/except because _req is
            # not defined in WSGI request.
            certdn = request._req.ssl_var_lookup ('SSL_CLIENT_S_DN')
            issuer = request._req.ssl_var_lookup ('SSL_CLIENT_I_DN')
            pass
        except:
            pass

    if certdn and certdn.startswith(issuer):
        # proxy.
        # Proxies can be signed by proxies.
        # Each level of "proxification" causes the subject
        # to have a '/CN=[0-9]+ appended to the signers subject.
        # These must be removed to discover the original identity's cert DN.
        certdn = proxyPattern.match(issuer).group(1)

    return certdn

class LigoAuthMiddleware:
    """This is the ultimate gatekeeper for GraceDb auth/authz.
    Ideally, Apache will do all authentication and the GraceDb
    Django code will do authorization.  That is for the future.
    Today -- it all happens here."""

    def process_request(self, request):
        user = None

        # An authenticated LIGO user will have one of these set.

        remote_user = request.META.get('REMOTE_USER')
        message = remote_user
        dn = cert_dn_from_request(request)

        if remote_user:
            user = authenticate(principal=remote_user)
            if not (user and user.is_authenticated()):
                message += "THIS SHOULD NEVER HAPPEN"
                pass

        if not user and dn:
            user = authenticate(dn=dn)

        if user and user.is_active:
            # Ideal, normal case.  Yay!
            pass
        elif request.path.find('latest') > 0:
            # We are on a "public" page.
            # XXX Needs to be better refined. (dealt with elsewhere, in fact)
            user = AnonymousUser()
        elif user:
            # Grotesque case.  User authenticates, but is not active.
            # How is this?  Good credentials, but LDAP says you shouldn't
            # have credentials?
            user = None
        else:
            user = None

        request.user = user

        if user is None:
            # Forbidden!
            is_cli = request.POST.get('cli_version') or \
                     request.GET.get('cli_version')
            if is_cli:
                message = "Your credentials are not valid."
                return HttpResponseForbidden("{ 'error': '%s'  }" % message)
            return render_to_response(
                    'forbidden.html',
                    {'error': message},
                    context_instance=RequestContext(request))

class RemoteUserBackend(DefaultRemoteUserBackend):
    create_unknown_user = False

class LigoX509Backend:

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, dn, username=None):
        return certdn_to_user(dn)

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

class LigoShibBackend:

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, principal):
        try:
            return User.objects.get(username=principal)
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
