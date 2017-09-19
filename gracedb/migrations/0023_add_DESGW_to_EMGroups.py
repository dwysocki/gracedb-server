# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

GROUP_NAME = "DESGW"

def add_group(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')
    grp, created = EMGroup.objects.get_or_create(name=GROUP_NAME)
    if created:
        grp.save()

def remove_group(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')
    EMGroup.objects.get(name=GROUP_NAME).delete()

class Migration(migrations.Migration):

    dependencies = [ 
        ('gracedb', '0022_add_O2VirgoTest_search'),
    ]   

    operations = [ 
        migrations.RunPython(add_group, remove_group),
    ]
