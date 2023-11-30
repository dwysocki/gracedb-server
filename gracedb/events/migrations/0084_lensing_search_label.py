# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

# Search names and descriptions
SEARCH_TYPES = [
    {'name': 'LensingSubthreshold', 'description': 'Lensing Subthreshold Search'},
]

NEW_LABEL = [
    {'name': 'LENSED_CANDIDATE', 'defaultColor': 'orange', 'description': 'Candidate event was uploaded as part of a lensed search.'},
]

def add_searches(apps, schema_editor):
    Search = apps.get_model('events', 'Search')
    Label = apps.get_model('events', 'Label')

    # Create labels
    for label_dict in NEW_LABEL:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        l.defaultColor = label_dict['defaultColor']
        l.description = label_dict['description']
        l.save()

    # Create searches
    for search_dict in SEARCH_TYPES:
        search, created = Search.objects.get_or_create(name=search_dict['name'])
        if 'description' in search_dict:
            search.description = search_dict['description']
            search.save()

def remove_searches(apps, schema_editor):
    Search = apps.get_model('events', 'Search')
    Label = apps.get_model('events', 'Label')

    # Delete labels
    Label.objects.filter(name__in=[l['name'] for l in NEW_LABEL]).delete()

    # Delete searches
    Search.objects.filter(name__in=[s['name'] for s in SEARCH_TYPES]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0083_snr_opt_label_desc'),
    ]

    operations = [
        migrations.RunPython(add_searches, remove_searches),
    ]
