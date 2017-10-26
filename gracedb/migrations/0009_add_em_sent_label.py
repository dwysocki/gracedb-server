# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

labels = { 
    'EM_SENT': 'green',
}

def add_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')
    for name, color in labels.iteritems():
        Label.objects.create(name=name, defaultColor=color)

def remove_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    for name, color in labels.iteritems():
        l = Label.objects.get(name=name)
        l.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0015_multiburstevent_single_ifo_times')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
