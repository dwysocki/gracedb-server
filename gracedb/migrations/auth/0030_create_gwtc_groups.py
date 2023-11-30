# migration for creating gwtc catalog managers' group. 
# copied and edited by hand from a previous migration.

from __future__ import unicode_literals

from django.db import migrations

GROUPS = {
    'catalog_managers': ['cbcflow', 'chad.hanna@ligo.org', 'rhiannon.udall@ligo.org',
                         'chad.hanna@ligo.org', 'rebecca.ewing@ligo.org',
                         'prathamesh.joshi@ligo.org', 'divya.singh@ligo.org',
                         'alexander.pace@ligo.org'],
}

def add_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    for group_name, usernames in GROUPS.items():
        g, _ = Group.objects.get_or_create(name=group_name)
        users = User.objects.filter(username__in=usernames)
        g.user_set.add(*users)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    for group_name in GROUPS:
        g = Group.objects.get(name=group_name)
        g.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0029_alter_user_username'),
    ]

    operations = [
        migrations.RunPython(add_groups, remove_groups),
    ]
