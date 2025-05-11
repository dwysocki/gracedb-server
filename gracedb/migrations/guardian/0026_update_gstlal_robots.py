from django.db import migrations

# Creates UserObjectPermission objects which allow specific users
# to add events for pycbc. Also removes users that aren't in the 
# collaboration anymore. They couldn't log in and up

PIPELINE_NAME = 'gstlal'

USERS_TO_ADD = [
     'cort.posnansky@ligo.org',
     'gstlalcbc_offline',
      ]

def add_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    pipeline, created  = Pipeline.objects.get_or_create(name=PIPELINE_NAME)

    # Now add the new people:
    for u in USERS_TO_ADD:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

def remove_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    pipeline, created  = Pipeline.objects.get_or_create(name=PIPELINE_NAME)
    # first remove the new people:
    for u in USERS_TO_ADD:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

        uop.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('guardian', '0025_populate_gwak_uploaders'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
