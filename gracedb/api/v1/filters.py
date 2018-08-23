import logging

from rest_framework import filters

# Set up logger
logger = logging.getLogger(__name__)


class DjangoObjectAndGlobalPermissionsFilter(
    filters.DjangoObjectPermissionsFilter):
    """
    Same as DjangoObjectPermissionsFilter, except it allows global permissions.
    """
    accept_global_perms = True

    def filter_queryset(self, request, queryset, view):
        # Mostly from rest_framework.filters.DjangoObjectPermissionsFilter
        #
        # We want to defer this import until run-time, rather than import-time.
        # See https://github.com/encode/django-rest-framework/issues/4608
        # (Also see #1624 for why we need to make this import explicitly)
        from guardian.shortcuts import get_objects_for_user

        extra = {}
        user = request.user
        model_cls = queryset.model
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        permission = self.perm_format % kwargs
        extra['accept_global_perms'] = self.accept_global_perms

        return get_objects_for_user(user, permission, queryset, **extra)
