# -*- coding: utf-8 -*-

from django.db import models, migrations

# Add a migration to create the EARLY_WARNING label. For some reason, the original
# migration from 2019 that created it is lost in the ether. Fixes:

# https://git.ligo.org/computing/gracedb/server/-/issues/311

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'SSM', 'defaultColor': 'blue', 'description': 'Event is from a subsolar mass low-latency pipeline.'},
]

def add_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Create labels
    for label_dict in LABELS:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        if not created:
            l.defaultColor = label_dict['defaultColor']
            l.description = label_dict['description']
            l.save()
        else:
            print("label exists in database, moving on")

def remove_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Delete labels
    Label.objects.filter(name__in=[l['name'] for l in LABELS]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0092_neutrinoevent')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
