import logging

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

# Set up logger
logger = logging.getLogger(__name__)


def group_required(group_name, login_url=None, raise_exception=False):
    def check_groups(user):
        in_group = user.groups.filter(name=group_name).exists()
        if in_group:
            return True

        if raise_exception:
            raise PermissionDenied
        return False
    return user_passes_test(check_groups, login_url=login_url)


def internal_user_required(function=None, raise_exception=True, **kwargs):
    actual_decorator = group_required(settings.LVC_GROUP, 
        raise_exception=raise_exception, **kwargs)
    if function:
        return actual_decorator(function)
    return actual_decorator


def lvem_observers_only(function=None, login_url=None, superuser_allowed=False,
    raise_exception=True):
    """Allow access only to non-LVC LV-EM observers"""

    def check_groups(user):
        in_lvem_obs = user.groups.filter(
            name=settings.LVEM_OBSERVERS_GROUP).exists()
        in_lvc = user.groups.filter(name=settings.LVC_GROUP).exists()

        if ((in_lvem_obs and not in_lvc) or
            (superuser_allowed and user.is_superuser)):
            return True

        if raise_exception:
            raise PermissionDenied
        return False

    actual_decorator = user_passes_test(check_groups, login_url=login_url)
    if function:
        return actual_decorator(function)
    return actual_decorator


def public_if_public_access_allowed(function=None, login_url=None,
    raise_exception=False):

    # Either unauthenticated access is allowed or if not,
    # the user is authenticated
    test_func = lambda u: \
        settings.UNAUTHENTICATED_ACCESS or u.is_authenticated
    actual_decorator = user_passes_test(test_func, login_url=login_url)

    if function:
        return actual_decorator(function)
    return actual_decorator
