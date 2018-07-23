import logging

from django.shortcuts import get_object_or_404

from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets

from superevents.models import Superevent
from superevents.utils import get_superevent_by_date_id_or_404
from .settings import SUPEREVENT_LOOKUP_URL_KWARG

# Set up logger
logger = logging.getLogger(__name__)


class NestedViewSet(viewsets.GenericViewSet):
    """
    Generic viewset which is nested *below* a parent "object". Provides
    functionality for getting the parent object from a queryset. Options
    are available for filtering the parent queryset by view permissions
    (to allow 404 responses) and for checking if the user has permissions
    which may be attached to the parent object.

    Example: /api/events/G123456/logs
        Here, the parent would be the event instance with graceid G123456.
    """
    parent_lookup_url_kwarg = None
    parent_lookup_field = None
    parent_queryset = None
    parent_access_permission = None
    check_permissions_on_parent_object = False

    def initial(self, request, *args, **kwargs):
        """
        Runs initial setup before method handler is called. Mostly identical
        to rest_framework.views.APIView.initial, except we add in the
        function to get the parent object *BEFORE* we check base permissions.
        This is because often trying to get the parent would return a 404,
        which is preferable to returning a 403, which can happen even when
        the parent doesn't exist at all.
        """
        self.format_kwarg = self.get_format_suffix(**kwargs)

        # Perform content negotiation and store the accepted info on the
        # request
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg

        # Determine the API version, if versioning is in use.
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme

        # Ensure that the incoming request is permitted
        self.perform_authentication(request)

        # **Only change from default initial() method in APIView**
        # Initialize parent object - we do this here because we often need
        # to check permissions on the parent object before permitting a
        # request. This is done by default for list views or detail views,
        # but not for create views, except from within the serializer, and we
        # want to deny access with a 404 before that.
        # We call get_parent_object() since it caches the parent and checks
        # permissions, if specified in the class attributes.
        parent = self.get_parent_object()

        # Finish up permission checks
        self.check_permissions(request)
        self.check_throttles(request)

    def get_parent_lookup_value(self):
        """Get value for parent lookup from URL kwargs"""
        # Perform lookup filtering
        lookup_url_kwarg = self.parent_lookup_url_kwarg or \
            self.parent_lookup_field

        # Enforce that URL included the parent lookup URL kwarg
        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )
        parent_lookup_value = self.kwargs.get(self.parent_lookup_url_kwarg,
            None)

        return parent_lookup_value

    def get_parent_queryset(self):
        """
        Cache and get queryset for parent lookup. Option for filtering parent
        queryset based on permissions.
        """
        if not hasattr(self, '_parent_queryset'):
            if self.parent_access_permission is None:
                self._parent_queryset = self.parent_queryset
            else:
                self._parent_queryset = get_objects_for_user(self.request.user,
                    self.parent_access_permission, self.parent_queryset)

        return self._parent_queryset

    def check_parent_object_permissions(self, request, parent_obj):
        """Check object permissions on parent object"""
        for permission in self.get_permissions():
            # Only check parent object permissions if the permission class
            # has that functionality, since this is our custom functionality
            # that is not a part of the default DRF permission classes
            if hasattr(permission, 'has_parent_object_permission'):
                if not permission.has_parent_object_permission(request, self,
                    parent_obj):
                   self.permission_denied(request, message=getattr(permission,
                        'message', None))

    def get_parent_object(self, check_obj_perms=None):
        """Get parent object either from cache or by lookup"""
        # Use class setting by default, but allow overrides
        check_obj_perms = check_obj_perms if check_obj_perms is not None \
            else self.check_permissions_on_parent_object

        # If parent object is not already cached as _parent, then get it
        if not hasattr(self, '_parent'):
            self._set_parent()

            # Check object perms (only on the first pass)
            if check_obj_perms:
                self.check_parent_object_permissions(self.request,
                    self._parent)

        return self._parent

    def _set_parent(self):
        """Look up parent object and cache it as self._parent"""
        parent_lookup_value = self.get_parent_lookup_value()
        parent_queryset = self.get_parent_queryset()
        parent = get_object_or_404(parent_queryset,
            **{self.parent_lookup_field: parent_lookup_value})
        self._parent = parent


class SupereventNestedViewSet(NestedViewSet):
    """
    Gets a parent superevent object for a nested object by using the
    URL kwargs.  Also does a check on object permissions for the superevent,
    since some actions, like annotation, are controlled by a custom permission
    on the parent superevent itself.
    """
    parent_lookup_field = None # not needed due to custom lookup function
    parent_lookup_url_kwarg = SUPEREVENT_LOOKUP_URL_KWARG
    parent_queryset = Superevent.objects.all()
    parent_access_permission = 'superevents.view_superevent'
    check_permissions_on_parent_object = True

    def _set_parent(self):
        parent_lookup_value = self.get_parent_lookup_value()
        parent_queryset = self.get_parent_queryset()
        parent = get_superevent_by_date_id_or_404(parent_lookup_value,
            parent_queryset)
        self._parent = parent
