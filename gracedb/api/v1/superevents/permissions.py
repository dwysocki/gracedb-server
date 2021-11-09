import logging

from django.conf import settings
from django.urls import resolve

from rest_framework import permissions

from superevents.models import Superevent, Signoff
from ..permissions import FunctionalModelPermissions, \
    FunctionalObjectPermissions, FunctionalParentObjectPermissions

# Set up logger
logger = logging.getLogger(__name__)

# NOTE: unauthenticated access is controlled by a top-level settings variable
# called 'UNAUTHENTICATED_ACCESS'.  The 'unauthenticated_users_only' parameter
# which is part of several of the following classes handles specific cases
# only when UNAUTHENTICATED_ACCESS == True.  However, it's kind of redundant
# since unauthenticated users won't have the required Django permissions to
# pass the checks that would be implemented after the
# 'authenticated_users_only' value is checked.  But we still use it anyway just
# for completeness.


class SupereventModelPermissions(FunctionalModelPermissions):
    """
    Custom permissions for the superevent list view - we require different
    permissions for superevent creation, depending on the category.

    NOTE: PATCH permissions are needed for the detail view update, but are
    checked at the object level.  We include it here with no permissions
    required, since otherwise we would get a 405 error before checking
    object permissions.
    """
    authenticated_users_only = False
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
    authenticated_users_only = False
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
    authenticated_users_only = False
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
    authenticated_users_only = False
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST']

    def get_post_object_permissions(self, request, parent_obj):
        return ['superevents.annotate_superevent']


class SupereventLabellingModelPermissions(FunctionalModelPermissions):
    """
    Permissions for adding a label to a superevent i.e., (creating a
    Labelling object).
    """
    authenticated_users_only = False
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST', 'DELETE']

    def get_post_permissions(self, request):
        self.message = ('You do not have permission to add labels to '
            'superevents.')
        return ['superevents.add_labelling']

    def get_delete_permissions(self, request):
        self.message = ('You do not have permission to remove labels from '
            'superevents.')
        return ['superevents.delete_labelling']


class SupereventLogModelPermissions(FunctionalModelPermissions):
    """
    Permissions for adding a log to a superevent. Also handles
    possible case where a log is created with tags attached.
    """
    authenticated_users_only = False
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST']
    tag_data_field = 'tagname'

    def get_post_permissions(self, request):
        # Get tag names from request data - should be a list (with client)
        # NOTE: it's just a string for the way it's constructed
        # from the web interface
        tag_names = request.data.get(self.tag_data_field, None)

        required_permissions = []
        if ((tag_names == 'analyst_comments' or
            tag_names == ['analyst_comments']) and request.headers.get('x-requested-with') == 'XMLHttpRequest'):
            #tag_names == ['analyst_comments']) and request.is_ajax()):
            # Special case for log messages posted from the web interface
            # using AJAX.  I.e., if a message is posted from the web view
            # and only the default 'analyst_comments' tag is attached,
            # that's fine.
            pass
        elif tag_names:
            # If any tags, require tag_log permission.
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
                self.message = ("You are not allowed to post log messages "
                    "with tags.")

        return required_permissions


class SupereventLogTagModelPermissions(FunctionalModelPermissions):
    """
    Model-level permissions for superevent log tags. Primarilyl covers
    addition of tags to a log, but also allows GET requests without
    permissions.  DELETE requests are allowed without permissions here since
    those are checked at the object level (see the following class).
    """
    # DELETE needed for object permissions below
    authenticated_users_only = False
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
    """
    Object-level permissions for superevent log tags. Covers removal of
    tags from a log.  Also allows individual tag retrieval without permissions.
    """
    authenticated_users_only = False
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
    Model-level permissions for VOEvents attached to a superevent. Checks
    permissions for creating VOEvents and allows permissionless retrieval and
    listing of VOEvents.
    """
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['superevents.add_voevent'],
    }
    authenticated_users_only = False
    message = 'You do not have permission to create VOEvents.'


class SupereventGroupObjectPermissionPermissions(FunctionalModelPermissions):
    """
    Permissions for accessing and managing superevent group object permissions.

    Handles GET requests to view the group object permissions and POST requests
    to change them.
    """
    authenticated_users_only = True
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST']

    def get_get_permissions(self, request):
        required_permissions = [
            'superevents.view_supereventgroupobjectpermission',
        ]
        self.message = 'You are not allowed to view superevent permissions.'
        return required_permissions

    def get_post_permissions(self, request):
        # Get action from request data
        action = request.data.get('action', None)

        required_permissions = []
        if (action == 'expose'):
            required_permissions.append('superevents.expose_superevent')
            self.message = 'You are not allowed to expose superevents.'
        elif (action == 'hide'):
            required_permissions.append('superevents.hide_superevent')
            self.message = 'You are not allowed to hide superevents.'

        return required_permissions


class SupereventSignoffModelPermissions(FunctionalModelPermissions):
    """
    Model-level permissions for superevent signoffs. Manages permissions for
    taking certain actions related to signoffs.

    Checks permissions for GET requests (viewing signoffs), POST requests
    (creating signoffs), PATCH requests (updating signoffs), and DELETE
    requests (deleting signoffs).

    Does not check any signoff type-based permissions (see
    SupereventSignoffTypeModelPermissions).
    """
    authenticated_users_only = True
    allowed_methods = ['OPTIONS', 'HEAD', 'GET', 'POST', 'PATCH', 'DELETE']

    def get_get_permissions(self, request):
        self.message = ('You do not have permission to view superevent '
            'signoffs.')
        return ['superevents.view_signoff']

    def get_post_permissions(self, request):
        self.message = ('You do not have permission to create superevent '
            'signoffs.')
        return ['superevents.add_signoff']

    def get_patch_permissions(self, request):
        self.message = ('You do not have permission to change superevent '
            'signoffs.')
        return ['superevents.change_signoff']

    def get_delete_permissions(self, request):
        self.message = ('You do not have permission to delete superevent '
            'signoffs.')
        return ['superevents.delete_signoff']


def get_signoff_type_permissions(signoff_type, instrument):
    """
    Helper function for returning permissions and error messages for
    superevent signoff actions.

    Based on the type of signoff that is being done (ADV or OP), and
    the instrument (for OP signoffs), returns the permissions that
    the user should have to take signoff-related actions for that
    instrument/signoff type.

    Does not check that they have permission for each action (create, update,
    etc.); that is handled by SupereventSignoffModelPermissions).

    Used by SupereventSignoffTypeModelPermissions and
    SupereventSignoffTypeObjectPermissions.
    """

    # Base permissions and error message
    permissions = []
    message = None

    # Determine required permissions based on signoff type
    # and instrument
    if (signoff_type == Signoff.SIGNOFF_TYPE_OPERATOR):
        if (instrument == Signoff.INSTRUMENT_H1):
            permissions.append('superevents.do_H1_signoff')
        elif (instrument == Signoff.INSTRUMENT_L1):
            permissions.append('superevents.do_L1_signoff')
        elif (instrument == Signoff.INSTRUMENT_V1):
            permissions.append('superevents.do_V1_signoff')
        message = 'You do not have permission to do {inst} signoffs.' \
            .format(inst=instrument)
    elif (signoff_type == Signoff.SIGNOFF_TYPE_ADVOCATE):
        permissions.append('superevents.do_adv_signoff')
        message = 'You do not have permission to do advocate signoffs.'

    return permissions, message


class SupereventSignoffTypeModelPermissions(FunctionalModelPermissions):
    """
    Enforces signoff type-based permissions for signoff creation (POST).
    """
    authenticated_users_only = True
    allowed_methods = SupereventSignoffModelPermissions.allowed_methods

    def get_post_permissions(self, request):
        # Get signoff_type and instrument from request data
        signoff_type = request.data.get('signoff_type')
        instrument = request.data.get('instrument', '')

        required_permissions, message = get_signoff_type_permissions(
            signoff_type, instrument)
        if message is not None:
            self.message = message

        return required_permissions


class SupereventSignoffTypeObjectPermissions(FunctionalObjectPermissions):
    """
    Enforces signoff type-based permissions for signoff updates and
    deletion (PATCH and DELETE).
    """
    authenticated_users_only = True
    allowed_methods = SupereventSignoffModelPermissions.allowed_methods

    def _get_signoff_type_permissions_for_object(self, request, obj):
        """Helper function to prevent code duplication"""
        required_permissions, message = get_signoff_type_permissions(
            obj.signoff_type, obj.instrument)
        if message is not None:
            self.message = message
        return required_permissions

    def get_patch_object_permissions(self, request, obj):
        return self._get_signoff_type_permissions_for_object(request, obj)

    def get_delete_object_permissions(self, request, obj):
        return self._get_signoff_type_permissions_for_object(request, obj)

