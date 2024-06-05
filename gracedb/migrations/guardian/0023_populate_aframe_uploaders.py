# supports: https://git.ligo.org/computing/gracedb/server/-/issues/349

from django.db import migrations

# Creates UserObjectPermission objects which allow specific users
# to add events for pipelines.  Based on current production database
# content (27 October 2017)

# List of pipeline names and lists of usernames who should
# be allowed to add events for them
PP_LIST = [
    {
        'pipeline': 'aframe',
        'usernames': [
            'aframe-scitoken',
            'aframe-1-scitoken',
            'emfollow',
        ]
    },
]

def add_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)
    for pp_dict in PP_LIST:
        pipeline, created = Pipeline.objects.get_or_create(name=pp_dict['pipeline'])

        # Loop over users
        for username in pp_dict['usernames']:

            # Robot users should have been already created by ligoauth 0003,
            # but we have to create human user accounts here
            user, _ = User.objects.get_or_create(username=username)

            # Create UserObjectPermission
            uop, uop_created = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

def remove_permissions(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('guardian', '0022_populate_icecube_uploaders'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
