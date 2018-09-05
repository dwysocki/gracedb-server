from django.conf import settings
from django.contrib.auth.models import Group

from guardian.shortcuts import assign_perm, remove_perm

# Permissions to assign for logs
LOG_PERMS = {
    settings.LVEM_OBSERVERS_GROUP: ['view'],
    settings.PUBLIC_GROUP: ['view'],
}


# Generic functions for assigning/removing ------------------------------------
# group permissions to/from an object -----------------------------------------
def assign_perms_to_obj(perms, group, obj):
    """
    perms is a list of strings like ['view', 'annotate', 'add']
    """
    # Convert perms to a list of strings like
    #  {app_label}.{perm}_{model_name}
    full_perm_fmt = '{app_label}.{perm}_{model_name}'
    kwargs = {
        'app_label': obj._meta.app_label,
        'model_name': obj._meta.model_name,
    }
    full_perms = [full_perm_fmt.format(perm=p, **kwargs) for p in perms]

    # Assign all permissions
    for perm in full_perms:
        assign_perm(perm, group, obj)


def remove_perms_from_obj(perms, group, obj):
    """
    perms is a list of strings like ['view', 'annotate', 'add']
    """
    # Convert perms to a list of strings like
    #  {app_label}.{perm}_{model_name}
    full_perm_fmt = '{app_label}.{perm}_{model_name}'
    kwargs = {
        'app_label': obj._meta.app_label,
        'model_name': obj._meta.model_name,
    }
    full_perms = [full_perm_fmt.format(perm=p, **kwargs) for p in perms]

    # Remove permissions
    for perm in full_perms:
        remove_perm(perm, group, obj)

# Functions for exposing and hiding a log object ------------------------------
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
