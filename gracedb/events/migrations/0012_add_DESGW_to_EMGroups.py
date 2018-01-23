# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

# Add DESGW to EMGroups

# EMGroup name
GROUP_NAME = "DESGW"

def add_group(apps, schema_editor):
    EMGroup = apps.get_model('events','EMGroup')

    # Create group
    grp, created = EMGroup.objects.get_or_create(name=GROUP_NAME)

def remove_group(apps, schema_editor):
    EMGroup = apps.get_model('events','EMGroup')

    # Delete group
    try:
        EMGroup.objects.get(name=GROUP_NAME).delete()
    except EMGroup.DoesNotExist:
        print("Error: can't 'get' EMGroup {0}, skipping".format(GROUP_NAME))

class Migration(migrations.Migration):

    dependencies = [ 
        ('events', '0011_add_O2VirgoTest_search'),
    ]   

    operations = [ 
        migrations.RunPython(add_group, remove_group),
    ]
