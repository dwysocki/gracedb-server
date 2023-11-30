# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'SNR_OPTIMIZED', 'description': 'Indicates that the event was SNR-optimized as followup to another uploaded event.'},
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
        ('events', '0082_add_PyGRB_pipeline')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
