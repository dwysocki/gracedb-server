from django.conf import settings

from .utils import is_internal


def LigoAuthContext(request):

    user_is_internal = False
    user_is_lvem = False
    user_is_advocate = False # user is an EM advocate
    if request.user:
        if is_internal(request.user):
            user_is_internal = True
        if request.user.groups.filter(name=settings.LVEM_GROUP).exists():
            user_is_lvem = True
        if request.user.groups.filter(name=settings.EM_ADVOCATE_GROUP).exists():
            user_is_advocate = True

    return {'user': request.user, 'user_is_internal': user_is_internal,
        'user_is_lvem': user_is_lvem, 'user_is_advocate': user_is_advocate}
