
from django.contrib.auth import authenticate

from gracedb.models import User
from django.contrib.auth.models import User as DjangoUser

import re
proxyPattern = re.compile(r'^(.*?)(/CN=\d+)*$')

def nameFromPrincipal(principal):
    name = principal.split('@')[0]
    first, last = name.split('.')
    return first[0].upper() + first[1:] + " " + last[0].upper() + last[1:]

class LigoAuthMiddleware:

    def process_request(self, request):

        ligouser = None
        user = None
        principal = None

        queryResult = []
        if not request.user.is_anonymous():
            # Scott's middleware has set the user aready using shib.
            # Let's add some more attributes.
            principal = request.user.username
            request.user.name = nameFromPrincipal(principal)
            queryResult = User.objects.filter(principal=principal)
        else:
            # authenticate with certs
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
                # These must be removed to discover the original identity's
                # subject DN.
                issuer = proxyPattern.match(issuer).group(1)
                queryResult = User.objects.filter(dn=issuer)
            elif certdn:
                # cert in browser.
                queryResult = User.objects.filter(dn=certdn)

        if queryResult:
            ligouser = queryResult[0]
            try:
                user = DjangoUser.objects.get(username=ligouser.unixid)
            except DjangoUser.DoesNotExist:
                user = DjangoUser(username=ligouser.unixid, password="")
                user.is_staff = False
                user.is_superuser = False
                user.save()
        elif principal:
            # There is no user ... what do we do?
            # If auth was via cert... nothing, DNs need to be registered.
            # If auth was via kerberos, we make sure it was a LIGO.ORG
            #   principal and make a new user and ligouser with no DN.
            #assert (principal.split('@')[1] == 'LIGO.ORG')
            ligouser = User(name = nameFromPrincipal(principal),
                            email = principal.lower(),
                            principal = principal,
                            dn = "NONE",
                            unixid = principal.split('@')[0])
            ligouser.save()
            try:
                user = DjangoUser.objects.get(username=ligouser.unixid)
            except DjangoUser.DoesNotExist:
                user = DjangoUser(username=ligouser.unixid, password="")
                user.is_staff = False
                user.is_superuser = False
                user.save()

        request.user = authenticate(ssluser=user)
        request.ligouser = ligouser

        # Http404 doesn't check for user == None, just hasattr(x,'user')
        # Why does this matter?  I forget, but it does.
        if not request.user: del request.user 

        return None

#   def process_view(self, request, view_func, view_args, view_kwargs):
#       return None

#   def process_response(self, request, response):
#       return None

#   def process_exception(self, request, exception):
#       return None

class LigoAuthBackend:

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, ssluser):
        return ssluser

    def get_user(self, user_id):
        try:
            return DjangoUser.get(id=user_id)
        except DjangoUser.UserDoesNotExist:
            return None

def LigoAuthContext(request):
    return { 'ligouser' : request.ligouser, 'user' : request.user }
