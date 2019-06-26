from functools import wraps


def ignore_maintenance_mode(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        return view(request, *args, **kwargs)
    inner.__dict__['ignore_maintenance_mode'] = True
    return inner
