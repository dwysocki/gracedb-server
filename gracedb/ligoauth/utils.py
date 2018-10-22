from django.http import HttpResponseForbidden
from django.utils.functional import wraps

def groups_allowed(group_names):
    """
    Decorator to allow access to specified group(s).
    Usage:
        @groups_allowed(settings.LVC_GROUP)
        @groups_allowed([settings.LVC_GROUP, settings.LVEM_OBSERVERS_GROUP])
    """

    if isinstance(group_names, str):
        group_names = [group_names]
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_groups = [g.name for g in request.user.groups.all()]
            if set(group_names).isdisjoint(user_groups):
                # Use a template
                return HttpResponseForbidden("You are not a member of {0}".format(group_names))
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator

