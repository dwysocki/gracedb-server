# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add labels for Virgo operator signoff

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'V1OPS', 'defaultColor': 'black', 'description': 'V1 operator signoff requested.'},
    {'name': 'V1OK', 'defaultColor': 'green', 'description': 'V1 operator says event is okay.'},
    {'name': 'V1NO', 'defaultColor': 'red', 'description': 'V1 operator says event is not okay.'},
]

def add_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    # Create labels
    for label_dict in LABELS:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        l.defaultColor = label_dict['defaultColor']
        l.description = label_dict['description']
        l.save()

def remove_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    # Delete labels
    Label.objects.filter(name__in=[l['name'] for l in LABELS]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0009_add_em_sent_label')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
