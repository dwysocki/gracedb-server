# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

# Add AllSkyLong search

# Search name and description
SEARCH = {
    'name': 'AllSkyLong',
    'description': 'all-sky long burst online'
}

def add_search(apps, schema_editor):
    Search = apps.get_model('gracedb','Search')

    # Create search
    new_search, created = Search.objects.get_or_create(name=SEARCH['name'])
    new_search.description = SEARCH['description']
    new_search.save()

def remove_search(apps, schema_editor):
    Search = apps.get_model('gracedb','Search')

    # Delete search
    try:
        Search.objects.get(name=SEARCH['name']).delete()
    except Search.DoesNotExist:
        print("Error: can't 'get' search {0}, skipping".format(SEARCH['name']))

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0007_initial_emgroup_data'),
    ]

    operations = [
        migrations.RunPython(add_search, remove_search),
    ]
