from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
import logging

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
