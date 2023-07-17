# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add labels for RAVBN in support of:
# https://git.ligo.org/computing/gracedb/server/-/issues/234

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'cWB_r', 'defaultColor': 'black', 'description': 'cWB-AllSky search performed by the cWB-XP'},
    {'name': 'cWB_s', 'defaultColor': 'black', 'description': 'cWB-AllSky search performed by the cWB-2G.subthr'},
]

def add_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Create labels
    for label_dict in LABELS:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        l.description = label_dict['description']
        l.save()

def remove_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # We're just changing the description, not creating it. So just pass.
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0080_new_cwb_fields')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
