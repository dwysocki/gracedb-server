# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

new_EMGroups = [
    '1M2H',
    'AAOGW',
    'AGILE',
    'ANTARES',
    'Apertif-EVN',
    'AST3',
    'Auger',
    'AZTEC-GW',
    'BlackGEM',
    'COSI',
    'CTA ',
    'CZTI-IUCAA',
    'DLT40',
    'DWF',
    'FAST',
    'GROND',
    'Huntsman',
    'HXMT',
    'IceCube',
    'IKI_GRB',
    'IPN',
    'MeerKAT',
    'NenuFAR',
    'NRAO',
    'NTE',
    'OGWARTS',
    'RIMAS',
    'SRG-eROSITA',
    'TLC X-ray Imaging',
    'UNC-LFP',
]

def add_MOU_EMGroups(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')
    for g_name in new_EMGroups:
        grp, created = EMGroup.objects.get_or_create(name=g_name)
        if created:
            grp.save()

def remove_MOU_EMGroups(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')
    for g_name in new_EMGroups:
        try:
            EMGroup.objects.get(name=g_name).delete()
        except:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0013_add_ATLAS_to_EMGroups'),
    ]

    operations = [
        migrations.RunPython(add_MOU_EMGroups, remove_MOU_EMGroups),
    ]
