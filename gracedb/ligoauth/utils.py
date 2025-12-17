from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from django.utils.functional import wraps

from guardian.models import UserObjectPermission
from events.models import Pipeline


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


def is_internal(user):
    return user.groups.filter(name=settings.LVC_GROUP).exists()


def add_user_to_pipeline_uploaders(user, pipeline):
    """
    Function that creates a UserObjectPermission object to upload
    to a pipeline.

    Inputs:
        user: a django.contrib.auth.model.User object or string
              of the user's username
        pipeline: a event.models.Pipeline object or string of
              the name of the pipeline
    """

    # If 'user' is a string, try and fetch the User object:
    if isinstance(user, str):
        user = User.objects.get(username=user)
    elif not isinstance(user, User):
        raise ValueError(f'{user} is not a valid User object')

    # If 'pipeline' is a string, try and fetch the Pipeline object:
    if isinstance(pipeline, str):
        pipeline = Pipeline.objects.get(name=pipeline)
    if not isinstance(pipeline, Pipeline):
        raise ValueError(f'{pipeline} is not a valid Pipeline object')

    # Retrieve the objects we will need
    p = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get(app_label='events', model='pipeline')

    perm, created = UserObjectPermission.objects.get_or_create(
                        user=user, permission=p, content_type=ctype,
                        object_pk=pipeline.pk)

    if created:
        print(f'Added populate_pipeline permission for {user.username} and',
              f'{pipeline.name}')
    else:
        print(f'{user.username} already has permission to populate {pipeline.name}')


def remove_user_from_pipeline_uploaders(user, pipeline):
    """
    Function that removes UserObjectPermission object to upload
    to a pipeline.

    Inputs:
        user: a django.contrib.auth.model.User object or string
              of the user's username
        pipeline: a event.models.Pipeline object or string of
              the name of the pipeline
    """

    # If 'user' is a string, try and fetch the User object:
    if isinstance(user, str):
        user = User.objects.get(username=user)
    elif not isinstance(user, User):
        raise ValueError(f'{user} is not a valid User object')

    # If 'pipeline' is a string, try and fetch the Pipeline object:
    if isinstance(pipeline, str):
        pipeline = Pipeline.objects.get(name=pipeline)
    if not isinstance(pipeline, Pipeline):
        raise ValueError(f'{pipeline} is not a valid Pipeline object')

    # Retrieve the objects we will need
    p = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get(app_label='events', model='pipeline')

    try:
        perm = UserObjectPermission.objects.get(
                   user=user, permission=p, content_type=ctype,
                   object_pk=pipeline.pk)
    except UserObjectPermission.DoesNotExist:
        print(f'{user.username} does not have permission to populate',
              f'{pipeline.name}')
        return

    perm.delete()
    print(f'{user.username} removed from {pipeline.name} uploaders')


def get_pipeline_uploaders(pipeline):
    """
    Function that returns a queryset of user objects that currently have
    permission to populate a given pipeline

    Inputs:
        pipeline: a event.models.Pipeline object, or a string
                  of a pipeline's name
    """

    # If 'pipeline' is a string, try and fetch the Pipeline object:
    if isinstance(pipeline, str):
        pipeline = Pipeline.objects.get(name=pipeline)
    if not isinstance(pipeline, Pipeline):
        raise ValueError(f'{pipeline} is not a valid Pipeline object')

    # Retrieve the objects we will need
    p = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get(app_label='events', model='pipeline')

    uploaders = UserObjectPermission.objects.filter(
                    permission=p, content_type=ctype, object_pk=pipeline.pk)

    if uploaders.exists():
        return User.objects.filter(id__in=uploaders.filter(user_id__isnull=False).\
                   values_list('user_id', flat=True))
    else:
        return User.objects.none()


def get_pipeline_perms_for_user(user):
    """
    Function that returns a queryset of pipelines to which the input user
    has permission to upload.

    Inputs:
        user: a django.contrib.auth.model.User object or string
              of the user's username
    """

    # If 'user' is a string, try and fetch the User object:
    if isinstance(user, str):
        user = User.objects.get(username=user)
    elif not isinstance(user, User):
        raise ValueError(f'{user} is not a valid User object')

    # Retrieve the objects we will need
    p = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get(app_label='events', model='pipeline')

    # get the data type of the pipeline primary key
    pipeline_pk_type = type(Pipeline.objects.first().id)

    pk_list = UserObjectPermission.objects.filter(permission=p,
                  content_type=ctype, user=user).values_list('object_pk', flat=True)

    if pk_list.exists():
        if not isinstance(pk_list[0], pipeline_pk_type):
            pk_list = [pipeline_pk_type(p) for p in pk_list]
        return Pipeline.objects.filter(id__in=pk_list)
    else:
        return Pipeline.objects.none()
