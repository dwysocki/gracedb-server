from django.conf import settings

def LigoAuthContext(request):

    user_is_internal = False
    user_is_lvem = False
    if request.user:
        if request.user.groups.filter(name=settings.LVC_GROUP).exists():
            user_is_internal = True
        if request.user.groups.filter(name=settings.LVEM_GROUP).exists():
            user_is_lvem = True

    return {'user': request.user, 'user_is_internal': user_is_internal,
        'user_is_lvem': user_is_lvem}
