# -*- coding: utf-8 -*-

from django.db import models, migrations

# https://chat.ligo.org/ligo/pl/u5eq5weu378c3y1uuxe4oi1ide
# having a search with the same name as a label breaks query parsing.
# The old one has already been migrated, so this is a new migration
# to change it back. 

OLD_LABEL = 'SSM'
NEW_LABEL = 'SUBSOLAR_MASS'

def new_label_name(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    ssm, created = Label.objects.get_or_create(name=OLD_LABEL)
    if not created:
        ssm.name = NEW_LABEL
        ssm.save()
    else:
        print('label not found, moving on')

def old_label_name(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    ssm, created = Label.objects.get_or_create(name=NEW_LABEL)
    if not created:
        ssm.name = OLD_LABEL
        ssm.save()
    else:
        print('label not found, moving on')

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0093_ssm_label')
    ]

    operations = [
        migrations.RunPython(new_label_name, old_label_name)
    ]
