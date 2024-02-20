import logging

from rest_framework_guardian import filters

# Set up logger
logger = logging.getLogger(__name__)


class DjangoObjectAndGlobalPermissionsFilter(
    filters.ObjectPermissionsFilter):
    """
    Same as ObjectPermissionsFilter, except it allows global permissions.
    """
    shortcut_kwargs = filters.ObjectPermissionsFilter.shortcut_kwargs
    shortcut_kwargs['accept_global_perms'] = True
