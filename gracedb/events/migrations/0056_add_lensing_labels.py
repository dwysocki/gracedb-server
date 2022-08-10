# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add labels for the lensing group during the O4 MDC

# Label names, default colors, and descriptions
LABELS = [
    {'name': '2022_LENSING_MDC', 'defaultColor': 'black', 'description': 'Event is part of the O4 Lensing MDC.'},
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
        ('events', '0055_event_reporting_latency')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
