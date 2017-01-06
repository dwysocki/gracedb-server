# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def add_ATLAS(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')
    atlas_grp, created = EMGroup.objects.get_or_create(name="ATLAS")
    if created:
        atlas_grp.save()

def remove_ATLAS(apps, schema_editor):
    atlas_grp = apps.get_model('gracedb','EMGroup')
    EMGroup.objects.get(name=atlas_grp.name).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0012_new_LIB_event_structure'),
    ]

    operations = [
        migrations.RunPython(add_ATLAS, remove_ATLAS),
    ]
