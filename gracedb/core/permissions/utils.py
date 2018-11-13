from guardian.shortcuts import assign_perm, remove_perm


# Generic functions for assigning/removing group permissions to/from an object
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
