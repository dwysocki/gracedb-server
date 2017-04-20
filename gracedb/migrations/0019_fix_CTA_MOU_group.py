# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

CTA_name = {
    'old': 'CTA ',
    'new': 'CTA',
}

def fix_CTA_name(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')

    cta = EMGroup.objects.get(name=CTA_name['old'])
    cta.name = CTA_name['new']
    cta.save()

def unfix_CTA_name(apps, schema_editor):
    EMGroup = apps.get_model('gracedb','EMGroup')

    cta = EMGroup.objects.get(name=CTA_name['new'])
    cta.name = CTA_name['old']
    cta.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0018_single_inspiral_channel'),
    ]

    operations = [
        migrations.RunPython(fix_CTA_name, unfix_CTA_name),
    ]
