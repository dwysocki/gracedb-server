# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

SEARCH = {'name': 'AllSkyLong',
          'description': 'all-sky long burst online'
}

def add_search(apps, schema_editor):
    Search = apps.get_model('gracedb','Search')
    new_search, created = Search.objects.get_or_create(name=SEARCH['name'])
    if created:
        for key in SEARCH.keys():
            setattr(new_search, key, SEARCH[key])
        new_search.save()

def remove_search(apps, schema_editor):
    Search = apps.get_model('gracedb','Search')
    Search.objects.get(name=SEARCH['name']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0010_lalinferenceburstevent'),
    ]

    operations = [
        migrations.RunPython(add_search, remove_search),
    ]
