
import re
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, AnonymousUser, Group
from django.contrib.auth.backends import RemoteUserBackend as DefaultRemoteUserBackend
from django.contrib.auth.backends import ModelBackend as DefaultModelBackend
from ligoauth.models import certdn_to_user

from django.shortcuts import render_to_response
from django.template import RequestContext

from django.http import HttpResponse, HttpResponseForbidden

proxyPattern = re.compile(r'^(.*?)(/CN=\d+)*$')

from datetime import datetime
from base64 import b64decode
import json

# XXX Hack. This will go away when we get the new perms infrastructure in place.
PUBLIC_URLS = [
    '/',
    '/SPInfo',
    '/SPInfo/',
    '/SPPrivacy',
    '/SPPrivacy/',
    '/DiscoveryService',
    '/DiscoveryService/',
]

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

def create_user_from_request(request):
    user_dict = {
        'username': request.META.get('REMOTE_USER'),
        'email': request.META.get('mail', ''),
        'first_name': request.META.get('givenName', ''),
        'last_name': request.META.get('sn', ''),
        'password': 'X',
    }
    return User.objects.create(**user_dict)

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

        # Apache should be configured so that the *only* thing that can
        # set remote_user is mod_shib. If we have remote user, we can 
        # also assume that we have a valid shib session. 
        if remote_user:
            user = authenticate(principal=remote_user)
            if not user:
                # We have a remote user who was not found in the database, but 
                # *does* have a valid shib session. So we'll create the user.
                try:
                    user = create_user_from_request(request)
                except Exception, e:
                    # XXX This error message could use some work.
                    return HttpResponseForbidden("{ 'error': '%s'  }" % str(e)) 

            if not (user and user.is_authenticated()):
                message += "THIS SHOULD NEVER HAPPEN"
                pass
            
            # Add shib user to groups. This operation is idempotent, but may
            # incur a performance hit. 
            isMemberOf = request.META.get('isMemberOf',None)
            if isMemberOf:
                for group_name in isMemberOf.split(';'):
                    try:
                        g = Group.objects.get(name=group_name)
                        g.user_set.add(user)
                    except:
                        pass

        if not user and dn:
            user = authenticate(dn=dn)

        authn_header = request.META.get('HTTP_AUTHORIZATION', None)
        if not user and 'apibasic' in request.path and authn_header:
            user = authenticate(authn_header=authn_header)
            # XXX Note: We are using date_joined to store the date
            # when the password was set, not when the user joined up. 
            # This could cause some strange behavior if we ever want to
            # actually use 'date_joined' for it's intended purpose.
            # check: is now greater than date_joined + time_delta?
            if user:
                if datetime.now() > user.date_joined + settings.PASSWORD_EXPIRATION_TIME:
                    msg = "Your password has expired. Please log in and request another."
                    return HttpResponseForbidden(json.dumps({'error': msg})) 

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

        # Check: Is the requested URL allowed for the PUBLIC?
        #if user is None:
        if user is None and request.path_info not in PUBLIC_URLS:
            # Forbidden!
            is_cli = request.POST.get('cli_version') or \
                     request.GET.get('cli_version')
            if is_cli:
                message = "Your credentials are not valid."
                return HttpResponseForbidden("{ 'error': '%s'  }" % message)
            if 'apibasic' in request.path:
                # The user was trying to get to the API exposed by basic auth. Send JSON with challenge.
                msg = "Login failed: Incorrect username or password."
                response = HttpResponse(json.dumps({'error': msg}), status=401)
                response['WWW-Authenticate'] = 'Basic realm="/apibasic/"'
                return response
            return render_to_response(
                    'forbidden.html',
                    {'error': message}, status=403,
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

class LigoBasicBackend:
    
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, authn_header):
        # dig out the username and password from the authn header
        username = None
        password = None

        try:
            authn_type, cred = authn_header.strip().split()
        except:
            return None

        if authn_type.lower() != 'basic':
            return None

        try:
            cred = b64decode(cred)
            username, password = cred.split(':')
        except:
            return None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        else:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

class ModelBackend(DefaultModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        return None
