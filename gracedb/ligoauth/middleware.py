import logging
import re

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.middleware import PersistentRemoteUserMiddleware
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured

from core.http import request_is_for_view

# Set up logger
logger = logging.getLogger(__name__)


# NOTE: this middleware uses the old middleware class construction because
# Django's RemoteUserMiddleware and PersistentRemoteUserMiddleware are still
# based on that layout.  Will probably need to update this at some point.
class ShibbolethWebAuthMiddleware(PersistentRemoteUserMiddleware):
    """
    Middleware class for authenticating users from a Shibboleth session. This
    should be used for all authentication for the GraceDB web interface.

    Some of the content is taken from Django's RemoteUserMiddleware and from
    the django-shibboleth-remoteuser package.
    """
    user_header = getattr(settings, 'SHIB_USER_HEADER', 'REMOTE_USER')
    group_header = getattr(settings, 'SHIB_GROUPS_HEADER', 'isMemberOf')
    group_delimiter = ';'

    def process_request(self, request):

        # This middleware should *only* be active at the post-login URL
        # where shibboleth is also active.
        if not request_is_for_view('post-login', request):
            return

        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")

        # Get username from request headers
        username = request.META.get(self.user_header, None)

        # If the header is blank or doesn't exist, return. We also catch
        # case where the username is '(null)', meaning the corresponding
        # Apache environment variable was empty but it still put the value
        # in the header (for some reason)
        if (username is None or username == '(null)'):
            return

        # If shib headers are available and the user is already authenticated,
        # double-check that the request user and the shib user are the same.
        if request.user.is_authenticated and (request.user.get_username() ==
            self.clean_username(username, request)):
            return

        # Otherwise, we are seeing this user for the first time in this,
        # session, so we attempt to authenticate the user. The backend will
        # create user accounts for unknown users with session information.
        user = auth.authenticate(request, remote_user=username)

        # If user not found in database, create user account
        if user:
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)

            # Update the user's groups
            self.update_user_groups(request, user)

    @classmethod
    def update_user_groups(cls, request, user):
        """
        Updates a user's groups within the database based on the information in
        the Shibboleth session. Session group data is treated as definitive.
        """

        # Don't do anything if the user is a robot account since their group
        # memberships are managed internally.
        if hasattr(user, 'robotuser'):
            return

        # Get groups from session which are in database as a QuerySet
        session_groups = Group.objects.filter(name__in=
            request.META.get(cls.group_header, '') \
            .split(cls.group_delimiter))

        # Add groups which are in session but not in database
        user.groups.add(*session_groups)

        # Remove groups in database which are not in session, except for groups
        # which are managed by admins, like EM advocates and executives
        user.groups.remove(*user.groups.exclude(name__in=
            [g.name for g in session_groups] + settings.ADMIN_MANAGED_GROUPS))

        # NOTE: The two above operations could be done much more nicely if
        # the queryset operation difference() worked in MySQL


class ControlRoomMiddleware(object):
    """
    Middleware class which checks the user's IP against a list of IPs
    corresponding to instrument control rooms.  If the user appears to be
    in a control room, we add them to the corresponding control room group
    for the duration of the request.

    We split up the request and response processing into separate functions
    so that unit testing is easier.
    """
    control_room_group_suffix = '_control_room'

    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        # Check IP address
        user_ip = self.get_client_ip(request)

        # Add user to control room group(s)
        for ifo, ip in settings.CONTROL_ROOM_IPS.iteritems():
            if (ip == user_ip):
                request.user.groups.add(Group.objects.get(name=
                    ifo.lower() + self.control_room_group_suffix))

        return request

    def process_response(self, request, response):
        # Remove user from control room group(s)
        if request.user.is_authenticated:
            request.user.groups.remove(*request.user.groups.filter(
                name__contains=self.control_room_group_suffix))
        return response

    def __call__(self, request):
        # Code to be executed for requests ------------------------------------

        # Make sure user is authenticated and in LVC group --------------------
        if not (request.user.is_authenticated and request.user.is_active and
            request.user.groups.filter(name=settings.LVC_GROUP).exists()):
            return self.get_response(request)

        # Process request -----------------------------------------------------
        response = self.get_response(self.process_request(request))

        # Process response ----------------------------------------------------
        response = self.process_response(request, response)

        return response

    @staticmethod
    def get_client_ip(request):
        """Gets IP address of client. If forwarded, uses most recent proxy."""

        # Check for forwarded IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', None)
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', None)

        return ip
