# -*- coding: utf-8 -*-
# modified from a previous migration by hand
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.contrib.auth.management import create_permissions

# New strategy to avoid database integrity errors: simply migrate
# permissions from the em_advocates group to the rrt group. 

# Group name
RRT = settings.RRT_MEMBERS_GROUP
EMA = settings.EM_ADVOCATE_GROUP


def add_perms(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    rrt_group = Group.objects.get(name=RRT)
    ema_group = Group.objects.get(name=EMA)

    for perm in ema_group.permissions.all():
        rrt_group.permissions.add(perm)

def remove_perms(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    rrt_group = Group.objects.get(name=RRT)
    ema_group = Group.objects.get(name=EMA)

    for perm in ema_group.permissions.all():
        rrt_group.permissions.remove(perm)

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0029_alter_user_username'),
        ('ligoauth', '0087_rrt_and_alert_groups'),
    ]

    operations = [
        migrations.RunPython(add_perms, remove_perms),
    ]
