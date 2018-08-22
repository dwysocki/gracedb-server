from django.conf import settings
from django.contrib.auth.models import Group

from guardian.shortcuts import assign_perm, remove_perm


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


def expose_event_or_superevent_to_lvem(obj):
    """
    obj is an Event or Superevent instance.

    Currently works for superevents; will eventually be used for events
    (once the permissions structure is overhauled.
    """
    perms = ['view', 'annotate']

    # Get LV-EM group
    lvem_group = Group.objects.get(name=settings.LVEM_OBSERVERS_GROUP)

    # Assign permissions
    assign_perms_to_obj(perms, lvem_group, obj)


def expose_event_or_superevent_to_public(obj):
    """
    obj is an Event or Superevent instance.

    Currently works for superevents; will eventually be used for events
    (once the permissions structure is overhauled.
    """
    perms = ['view']

    # Get public group
    public_group = Group.objects.get(name=settings.PUBLIC_GROUP)

    # Assign permissions
    assign_perms_to_obj(perms, public_group, obj)


def expose_log(log, group):
    """
    Assigns group view permission ([app_label].view_[model_name]) permission to
    log object.
    """
    kwargs = {
        'app_label': log._meta.app_label,
        'model_name': log._meta.model_name,
    }
    permission = "{app_label}.view_{model_name}".format(**kwargs)
    assign_perm(permission, group, log)


def expose_log_to_lvem(log):
    """Applies expose_log for LV-EM Observers group"""
    group = Group.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
    expose_log(log, group)


def expose_log_to_public(log):
    """Applies expose_log for public group"""
    group = Group.objects.get(name=settings.PUBLIC_GROUP)
    expose_log(log, group)


def hide_log(log, group):
    """
    Removes group view permission ([app_label].view_[model_name]) permission
    from log object.
    """
    kwargs = {
        'app_label': log._meta.app_label,
        'model_name': log._meta.model_name,
    }
    permission = "{app_label}.view_{model_name}".format(**kwargs)
    remove_perm(permission, group, log)


def hide_log_from_lvem(log):
    """Applies hide_log for LV-EM Observers group"""
    group = Group.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
    hide_log(log, group)


def hide_log_from_public(log):
    """Applies hide_log for public group"""
    group = Group.objects.get(name=settings.PUBLIC_GROUP)
    hide_log(log, group)
