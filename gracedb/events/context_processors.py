from django.contrib.auth.models import Group

def LigoAuthContext(request):

    internal_groups = Group.objects.filter(name__in=['Communities:LSCVirgoLIGOGroupMembers', 'executives'])

    user_is_internal = False
    if request.user:
        if set(list(internal_groups)) & set(list(request.user.groups.all())):
            user_is_internal = True

    return {'user': request.user, 'user_is_internal': user_is_internal}
