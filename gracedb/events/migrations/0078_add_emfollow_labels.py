# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# Add labels for RAVBN in support of:
# https://git.ligo.org/computing/gracedb/server/-/issues/234

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'LOW_SIGNIF_PRELIM_SENT', 'defaultColor': 'black', 'description':
        'A low-significance preliminary GCN has been sent.'},
    {'name': 'SIGNIF_LOCKED', 'defaultColor': 'black', 'description': 'The GraceID associated with this event has all annotations required for an alert, passes the significant public alert threshold, and will only be automatically updated when preliminary alerts are sent.'},
    {'name': 'LOW_SIGNIF_LOCKED', 'defaultColor': 'green', 'description': 'The GraceID associated with this event has all annotations required for an alert, passes the low-significance public alert threshold, and will only be automatically updated when preliminary alerts are sent.'},
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
        ('events', '0077_alter_label_name')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
