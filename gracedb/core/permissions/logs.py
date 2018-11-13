from django.conf import settings
from django.contrib.auth.models import Group

from .utils import assign_perms_to_obj, remove_perms_from_obj

# Permissions to assign for logs
LOG_PERMS = {
    settings.LVEM_OBSERVERS_GROUP: ['view'],
    settings.PUBLIC_GROUP: ['view'],
}


def expose_log(log, group):
    """
    Assigns permissions to log object to expose it to a group.
    Permissions which are assigned are contained in the LOG_PERMS dict
    above, with the key corresponding to the group name.
    """
    assign_perms_to_obj(LOG_PERMS[group.name], group, log)


def hide_log(log, group):
    """
    Removes permissions to hide a log from a group. Permissions to remove
    are contained in the LOG_PERMS dict above, with the key corresponding
    to the group name.
    """
    remove_perms_from_obj(LOG_PERMS[group.name], group, log)


def expose_log_to_lvem(log):
    """Applies expose_log for LV-EM Observers group"""
    group = Group.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
    expose_log(log, group)


def expose_log_to_public(log):
    """Applies expose_log for public group"""
    group = Group.objects.get(name=settings.PUBLIC_GROUP)
    expose_log(log, group)


def hide_log_from_lvem(log):
    """Applies hide_log for LV-EM Observers group"""
    group = Group.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
    hide_log(log, group)


def hide_log_from_public(log):
    """Applies hide_log for public group"""
    group = Group.objects.get(name=settings.PUBLIC_GROUP)
    hide_log(log, group)
