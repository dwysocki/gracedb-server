# -*- coding: utf-8 -*-

from django.db import migrations

# Search names and descriptions
SEARCH_TYPES = [
    {'name': 'VTInjection', 'description': 'VTInjection Search'},
]


def add_searches(apps, schema_editor):
    Search = apps.get_model('events', 'Search')
    Label = apps.get_model('events', 'Label')

    # Create searches
    for search_dict in SEARCH_TYPES:
        search, created = Search.objects.get_or_create(name=search_dict['name'])
        if 'description' in search_dict:
            search.description = search_dict['description']
            search.save()

def remove_searches(apps, schema_editor):
    Search = apps.get_model('events', 'Search')
    Label = apps.get_model('events', 'Label')

    # Delete searches
    Search.objects.filter(name__in=[s['name'] for s in SEARCH_TYPES]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0087_add_detection_statistic'),
    ]

    operations = [
        migrations.RunPython(add_searches, remove_searches),
    ]
