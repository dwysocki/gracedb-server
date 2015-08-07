# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def add_labels(apps, schema_editor):
    ifos = ['H1', 'L1']
    labels = { 
        'OPS': 'black',
        'OK': 'green',
        'NO': 'red',
    }
    Label = apps.get_model('gracedb', 'Label')
    for ifo in ifos:
        for name, color in labels.iteritems():
            label_name = ifo + name
            Label.objects.create(name=label_name, defaultColor=color)

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0005_auto_20150811_0929'),
    ]

    operations = [
        migrations.RunPython(add_labels)
    ]
