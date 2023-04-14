# -*- coding: utf-8 -*-
# modified from a previous migration by hand
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.contrib.auth.management import create_permissions


# Group name
RRT = settings.RRT_MEMBERS_GROUP

ADVOCATE_PERMS = [
    # Signoff permissions
    'add_signoff',
    'change_signoff',
    'delete_signoff',
    'do_adv_signoff',
    ]


# We have to run this to force the permissions to actually be created.
# Otherwise they are created by a post-migrate signal and it's not possible
# to run all of the migrations in a single command
def create_perms(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def add_perms(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    rrt_group = Group.objects.get(name=RRT)

    # Add superevent permissions to groups. Or groups to permissions?
    for codename in ADVOCATE_PERMS:
        p = Permission.objects.get(codename=codename,
            content_type__app_label='superevents')
        p.group_set.add(rrt_group)


def remove_perms(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    rrt_group = Group.objects.get(name=RRT)

    # remove permissions from group
    for codename in ADVOCATE_PERMS:
        p = Permission.objects.get(codename=codename,
            content_type__app_label='superevents')
        p.group_set.remove(rrt_group)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0029_alter_user_username'),
        ('ligoauth', '0087_rrt_and_alert_groups'),
    ]

    operations = [
        migrations.RunPython(create_perms, migrations.RunPython.noop),
        migrations.RunPython(add_perms, remove_perms),
    ]
