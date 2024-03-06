# -*- coding: utf-8 -*-

from django.db import migrations
from events.models import Pipeline, Search

# Creates initial search pipeline instances

# List of search pipeline names
NEW_PIPELINES = [
    ('IceCube', Pipeline.PIPELINE_TYPE_EXTERNAL),
]

NEW_SEARCHES = [
    'HEN',
]

def add_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')
    Search = apps.get_model('events', 'Search')

    # Create pipelines
    for pipeline_name in NEW_PIPELINES:
        pipeline, created = Pipeline.objects.get_or_create(name=pipeline_name[0])
        pipeline.pipeline_type = pipeline_name[1]
        pipeline.save()

    # Create searches
    for search_name in NEW_SEARCHES:
        search, created = Search.objects.get_or_create(name=search_name)
        search.save()

def remove_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')
    Search = apps.get_model('events', 'Search')

    # Delete pipelines
    for pipe in NEW_PIPELINES:
        Pipeline.objects.filter(name=pipe[0]).delete()

    # Delete searches
    for search in NEW_SEARCHES:
        Search.objects.get(name=search).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0090_add_svom_pipeline'),
    ]

    operations = [
        migrations.RunPython(add_pipelines, remove_pipelines),
    ]
