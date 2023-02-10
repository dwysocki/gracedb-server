# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add labels for RAVBN in support of:
# https://git.ligo.org/computing/gracedb/server/-/issues/234

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'EM_SelectedConfident', 'defaultColor': 'green', 'description': 'The event has all annotations necessary for an alert and passes the significant alert threshold.'},
]

def add_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Create labels
    for label_dict in LABELS:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        l.defaultColor = label_dict['defaultColor']
        l.description = label_dict['description']
        l.save()

def remove_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Delete labels
    Label.objects.filter(name__in=[l['name'] for l in LABELS]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0068_rip_mbtaonline')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
