# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

ifos = ['V1']
labels = {
    'OPS': 'black',
    'OK': 'green',
    'NO': 'red',
}

def add_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')
    for ifo in ifos:
        for name, color in labels.iteritems():
            label_name = ifo + name
            Label.objects.create(name=label_name, defaultColor=color)

def remove_labels(apps, schema_editor):
    Label = apps.get_model('gracedb', 'Label')

    for ifo in ifos:
        for name, color in labels.iteritems():
            label_name = ifo + name
            l = Label.objects.get(name=label_name)
            l.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0016_add_em_sent_label')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
