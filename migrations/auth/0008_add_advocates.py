# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

advocate_usernames = [
    'branson.stephens@LIGO.ORG',
]

def add_advocates_group_and_users(apps, schema_editor):
    from django.conf import settings

    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")

    advocates = Group.objects.create(name=settings.EM_ADVOCATE_GROUP)

    for username in advocate_usernames:
        try:
            user = User.objects.get(username=username)
            advocates.user_set.add(user)
        except:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0007_auto_20150708_1134'),
    ]

    operations = [
        migrations.RunPython(add_advocates_group_and_users),
    ]
