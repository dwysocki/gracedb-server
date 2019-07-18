# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

# Add O2VirgoTest search for initial production tests of 3-IFO searches
# May be removed at some point in the future?

# Search name and description
SEARCH = {
    'name': 'O2VirgoTest',
    'description': 'Testing 3-IFO pipelines for adding Virgo in O2'
}

def add_search(apps, schema_editor):
    Search = apps.get_model('events','Search')

    # Create search
    new_search, created = Search.objects.get_or_create(name=SEARCH['name'])
    if created:
        for key in SEARCH:
            setattr(new_search, key, SEARCH[key])
        new_search.save()

def remove_search(apps, schema_editor):
    Search = apps.get_model('events','Search')

    # Delete search
    try:
        Search.objects.get(name=SEARCH['name']).delete()
    except Search.DoesNotExist:
        print("Error: can't 'get' search {0}, skipping".format(SEARCH['name']))

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0010_add_virgo_labels'),
    ]

    operations = [
        migrations.RunPython(add_search, remove_search),
    ]
