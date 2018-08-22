import logging

from django.conf import settings
from django.urls import resolve

from rest_framework import exceptions, permissions

from superevents.models import Superevent

# Set up logger
logger = logging.getLogger(__name__)

# NOTE: considering only LVC and lv-em users for now.  Will have to
# think about public in the future.


class FunctionalModelPermissions(permissions.BasePermission):
    """
    Model-based table-level permissions which allow for custom functionality.

    Custom permission requirements should be defined in methods called
    'get_METHOD_permissions', where METHOD is the HTTP method for which the
    permissions apply.  If such a class method does not exist, no permissions
    are required for that method.

    Designed around rest_framework.permissions.DjangoModelPermissions and
    takes a lot of the logic from there.
    """
    authenticated_users_only = True
    allowed_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH',
        'DELETE']

    def get_required_permissions(self, request):
        # Is permission in allowed methods?
        if request.method not in self.allowed_methods:
            raise exceptions.MethodNotAllowed(request.method)

        # Get method for checking permissions - named like
        # get_{http_method}_permissions()
        perm_getter_function_name = "get_{method}_permissions".format(
            method=request.method.lower())

        # If method exists, call it and get permissions
        if hasattr(self, perm_getter_function_name):
            perm_getter_function = getattr(self, perm_getter_function_name)
            perms = perm_getter_function(request)
        else:
            # If the method is not defined, no permissions are required
            perms = []

        return perms

    def has_permission(self, request, view):
        # Run by at the start of request processing by view.initial(),
        # which calls view.check_permissions().

        # Workaround to ensure there permissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_model_permissions', False):
            return True

        # Check user authentication status
        if not request.user or (not request.user.is_authenticated and
            self.authenticated_users_only):
            return False

        # Get required permissions
        perms = self.get_required_permissions(request)

        # Return True/False
        return request.user.has_perms(perms)


class FunctionalObjectPermissions(permissions.BasePermission):
    """
    Model-based row-level permissions which allow for custom functionality.

    Custom permission requirements should be defined in methods called
    'get_METHOD_object_permissions', where METHOD is the HTTP method for which
    the permissions apply.  If such a class method does not exist, we fall back
    to the base class and check the self.perms_map attribute for a list of
    required permissions.  We also pass the object to the permission checker,
    since its attributes may be used to determine which permissions should
    be required.
    """
    authenticated_users_only = True
    allowed_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH',
        'DELETE']

    def get_required_object_permissions(self, request, obj):
        # Is permission in allowed methods?
        if request.method not in self.allowed_methods:
            raise exceptions.MethodNotAllowed(request.method)

        # Get method for checking permissions - named like
        # get_{http_method}_object_permissions()
        perm_getter_function_name = "get_{method}_object_permissions".format(
            method=request.method.lower())

        # If method exists, call it and get permissions
        if hasattr(self, perm_getter_function_name):
            perm_getter_function = getattr(self, perm_getter_function_name)
            perms = perm_getter_function(request, obj)
        else:
            # If the method is not defined, no permissions are required
            perms = []

        return perms

    def has_object_permission(self, request, view, obj):
        # This is called within view.get_object(), which calls
        # view.check_object_permissions()

        # Check user authentication status
        if not request.user or (not request.user.is_authenticated and
            self.authenticated_users_only):
            return False

        # Get permissions
        perms = self.get_required_object_permissions(request, obj)

        # Return True/False
        return request.user.has_perms(perms, obj)


class FunctionalParentObjectPermissions(FunctionalObjectPermissions):
    """
    Inherits almost everything from FunctionalObjectPermissions, but
    we want to simply rename has_object_permission to
    "has_parent_object_permission", so we have to override that method.

    Permission-getting methods should be named as for
    FunctionalObjectPermissions; i.e., like 'get_post_object_permissions'.
    """

    def has_object_permission(self, request, view, obj):
        return True

    def has_parent_object_permission(self, request, view, parent_obj):
        return super(FunctionalParentObjectPermissions, self) \
            .has_object_permission(request, view, parent_obj)


class SupereventModelPermissions(FunctionalModelPermissions):
    """
    Custom permissions for the superevent list view - we require different
    permissions for superevent creation, depending on the category.

    NOTE: PATCH permissions are needed for the detail view update, but are
    checked at the object level.  We include it here with no permissions
    required, since otherwise we would get a 405 error before checking
    object permissions.
    """
    allowed_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PATCH']

    def get_post_permissions(self, request):
        """
        Manages permissions for creating superevents.
        However, two types of POST requests can come through here:
          1. Superevent creation
          2. Confirmation of a superevent as GW

        We want to handle #1 here, but pass #2 to the object permission
        checker.  So we capture the url_name and require no permissions
        here for #2.
        """
        # First check request path since POST requests can go through this
        # viewset for either superevent creation or confirmation as a GW.
        resolver_match = resolve(request.path)
        required_perms = []
        if (resolver_match and
            resolver_match.url_name == 'superevent-confirm-as-gw'):
            # No permissions required here, permission checking for this
            # should be handled by the object permission checker.
            pass
        else:
            # Required permission depends on category, so we extract it from
            # request.data
            superevent_category = request.data.get('category', None)
            if superevent_category == Superevent.SUPEREVENT_CATEGORY_TEST:
                required_perms.append('superevents.add_test_superevent')
                self.message = ('You are not allowed to create test '
                    'superevents.')
            elif superevent_category == Superevent.SUPEREVENT_CATEGORY_MDC:
                required_perms.append('superevents.add_mdc_superevent')
                self.message = 'You are not allowed to create MDC superevents.'
            else:
                required_perms.append('superevents.add_superevent')
                self.message = 'You are not allowed to create superevents.'

        return required_perms


class SupereventObjectPermissions(FunctionalObjectPermissions):
    """
    Custom object permissions for the superevent detail views.

    POST: confirm superevent as GW
    PATCH: superevent updates
    """
    allowed_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'PATCH']
    
    def get_patch_object_permissions(self, request, obj):
        required_perms = []
        if obj.category == Superevent.SUPEREVENT_CATEGORY_TEST:
            required_perms.append('superevents.change_test_superevent')
            self.message = ('You are not allowed to change test '
                'superevents.')
        elif obj.category == Superevent.SUPEREVENT_CATEGORY_MDC:
            required_perms.append('superevents.change_mdc_superevent')
            self.message = 'You are not allowed to change MDC superevents.'
        else:
            required_perms.append('superevents.change_superevent')
            self.message = 'You are not allowed to change superevents.'

        return required_perms

    def get_post_object_permissions(self, request, obj):
        required_perms = []
        if obj.category == Superevent.SUPEREVENT_CATEGORY_TEST:
            required_perms.append('superevents.confirm_gw_test_superevent')
            self.message = ('You are not allowed to confirm test '
                'superevents as GWs.')
        elif obj.category == Superevent.SUPEREVENT_CATEGORY_MDC:
            required_perms.append('superevents.confirm_gw_mdc_superevent')
            self.message = ('You are not allowed to confirm MDC '
                'superevents as GWs.')
        else:
            required_perms.append('superevents.confirm_gw_superevent')
            self.message = ('You are not allowed to confirm superevents '
                'as GWs.')
        return required_perms


class EventParentSupereventPermissions(FunctionalParentObjectPermissions):
    """
    Custom permissions for the superevent events list view. This checks
    permissions on the *parent* superevent object to see what actions the
    user is allowed to take on it.

    We required different permissions for adding events to a superevent,
    depending on the category.
    """
    allowed_methods = ['GET', 'OPTIONS', 'HEAD', 'POST', 'DELETE']

    def get_post_object_permissions(self, request, parent_obj):
        """
        Checks whether a user is authorized to create an event-superevent
        relationship.  This is controlled by permissions like
        superevents.change_{category}_superevent on the superevent object.
        """
        superevent = parent_obj

        # Get required permissions
        required_perms = []
        if superevent.category == Superevent.SUPEREVENT_CATEGORY_TEST:
            required_perms.append('superevents.change_test_superevent')
            self.message = ('You are not allowed to add events to test '
                'superevents.')
        elif superevent.category == Superevent.SUPEREVENT_CATEGORY_MDC:
            required_perms.append('superevents.change_mdc_superevent')
            self.message = ('You are not allowed to add events to MDC '
                'superevents.')
        else:
            required_perms.append('superevents.change_superevent')
            self.message = 'You are not allowed to add events to superevents.'

        return required_perms

    def get_delete_object_permissions(self, request, parent_obj):
        """
        Checks whether a user is authorized to destroy an event-superevent
        relationship.  This is controlled by permissions like
        superevents.change_{category}_superevent on the superevent object.
        """
        superevent = parent_obj

        # Get required permissions
        required_perms = []
        if superevent.category == Superevent.SUPEREVENT_CATEGORY_TEST:
            required_perms.append('superevents.change_test_superevent')
            self.message = ('You are not allowed to remove events from test '
                'superevents.')
        elif superevent.category == Superevent.SUPEREVENT_CATEGORY_MDC:
            required_perms.append('superevents.change_mdc_superevent')
            self.message = ('You are not allowed to remove events from MDC '
                'superevents.')
        else:
            required_perms.append('superevents.change_superevent')
            self.message = ('You are not allowed to remove events from '
                'superevents.')

        return required_perms


class ParentSupereventAnnotatePermissions(FunctionalParentObjectPermissions):
    """For adding log messages and EMObservations"""

    def get_post_object_permissions(self, request, parent_obj):
        return ['superevents.annotate_superevent']


class SupereventLabellingModelPermissions(FunctionalModelPermissions):
    """
    Permissions for adding a label to a superevent i.e., (creating a
    Labelling object).
    """
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST', 'DELETE']

    def get_post_permissions(self, request):
        self.message = ('You do not have permission to add labels to '
            'superevents.')
        return ['superevents.add_labelling']

    def get_delete_permissions(self, request):
        self.message = ('You do not have permissions to remove labels from '
            'superevents.')
        return ['superevents.delete_labelling']


class SupereventLogModelPermissions(FunctionalModelPermissions):
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST']
    tag_data_field = 'tagname'

    def get_post_permissions(self, request):
        # Get tag names from request data
        tag_names = request.data.get(self.tag_data_field, None)

        required_permissions = []
        if tag_names is not None:

            # If any tags, require add_tag permission.
            required_permissions.append('superevents.tag_log')

            if (settings.EXTERNAL_ACCESS_TAGNAME in tag_names or
                settings.PUBLIC_ACCESS_TAGNAME in tag_names):
                # For tags which expose log messages, require specific
                # permissions to do that.
                if settings.EXTERNAL_ACCESS_TAGNAME in tag_names:
                    required_permissions.append('superevents.expose_log')
                    self.message = ('You are not allowed to expose superevent '
                        'log messages to LV-EM partners by applying the '
                        '\'{0}\' tag.').format(
                        settings.EXTERNAL_ACCESS_TAGNAME)

                if settings.PUBLIC_ACCESS_TAGNAME in tag_names:
                    required_permissions.append('superevents.expose_log')
                    self.message = ('You are not allowed to expose superevent '
                        'log messages to the public by applying the \'{0}\' '
                        'tag.').format(settings.PUBLIC_ACCESS_TAGNAME)
            else:
                self.message = "You are not allowed to tag log messages."

        return required_permissions


class SupereventLogTagModelPermissions(FunctionalModelPermissions):
    # DELETE needed for object permissions below
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST', 'DELETE']
    tag_data_field = 'name'

    def get_post_permissions(self, request):
        # Get tag name from request data
        tag_name = request.data.get(self.tag_data_field, None)

        # Require add_tag permission
        required_permissions = ['superevents.tag_log']

        if (tag_name == settings.EXTERNAL_ACCESS_TAGNAME or
            tag_name == settings.PUBLIC_ACCESS_TAGNAME):
            # For tags which expose log messages, require specific
            # permissions to do that.
            if (tag_name == settings.EXTERNAL_ACCESS_TAGNAME):
                required_permissions.append('superevents.expose_log')
                self.message = ('You are not allowed to expose superevent '
                    'log messages to LV-EM partners by applying the '
                    '\'{0}\' tag.').format(
                    settings.EXTERNAL_ACCESS_TAGNAME)

            if (tag_name == settings.PUBLIC_ACCESS_TAGNAME):
                required_permissions.append('superevents.expose_log')
                self.message = ('You are not allowed to expose superevent '
                    'log messages to the public by applying the \'{0}\' '
                    'tag.').format(settings.PUBLIC_ACCESS_TAGNAME)
        else:
            self.message = 'You are not allowed to tag log messages.'

        return required_permissions


class SupereventLogTagObjectPermissions(FunctionalObjectPermissions):
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'DELETE']

    def get_delete_object_permissions(self, request, obj):
        # Require add_tag permission
        required_permissions = ['superevents.untag_log']

        if (obj.name == settings.EXTERNAL_ACCESS_TAGNAME or
            obj.name == settings.PUBLIC_ACCESS_TAGNAME):
            # For tags which expose log messages, require specific
            # permissions to do that.
            if (obj.name == settings.EXTERNAL_ACCESS_TAGNAME):
                required_permissions.append('superevents.hide_log')
                self.message = ('You are not allowed to hide superevent '
                    'log messages from LV-EM partners by removing the '
                    '\'{0}\' tag.').format(
                    settings.EXTERNAL_ACCESS_TAGNAME)

            if (obj.name == settings.PUBLIC_ACCESS_TAGNAME):
                required_permissions.append('superevents.hide_log')
                self.message = ('You are not allowed to hide superevent '
                    'log messages from the public by removing the \'{0}\' '
                    'tag.').format(settings.PUBLIC_ACCESS_TAGNAME)
        else:
            self.message = ('You are not allowed to remove tags from log '
                'messages.')

        return required_permissions

    def has_object_permission(self, request, view, obj):
        """
        Customized so that we can check permissions on the parent log object.
        obj is still the Tag instance, and is used to determine which
        permissions are required, but the actual permissions are attached
        to the parent Log instance.
        """
        # This is called within view.get_object(), which calls
        # view.check_object_permissions()

        # Check user authentication status
        if not request.user or (not request.user.is_authenticated and
            self.authenticated_users_only):
            return False

        # Get permissions, use 
        perms = self.get_required_object_permissions(request, obj)

        # Return True/False
        return request.user.has_perms(perms, view._parent_log)


class SupereventVOEventModelPermissions(permissions.DjangoModelPermissions):
    """
    Permissions for adding a label to a superevent i.e., (creating a
    Labelling object).
    """
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['superevents.add_voevent'],
    }
    message = 'You do not have permission to create VOEvents.'


class SupereventVOEventModelPermissions(permissions.DjangoModelPermissions):
    """
    Permissions for adding a label to a superevent i.e., (creating a
    Labelling object).
    """
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['superevents.add_voevent'],
    }
    message = 'You do not have permission to create VOEvents.'
