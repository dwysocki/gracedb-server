# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add label for pycbc in support of:
# https://git.ligo.org/computing/gracedb/server/-/issues/269

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'SNR_OPTIMIZED', 'defaultColor': 'black', 'description': 'Indicates that the event was uploaded by the PyCBC SNR optimizer as followup to another PyCBC event.'},
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
        ('events', '0075_voevent_significant')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
