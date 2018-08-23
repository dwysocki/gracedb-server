import logging

from rest_framework import exceptions, permissions

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
