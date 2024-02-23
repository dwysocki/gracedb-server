# -*- coding: utf-8 -*-

from django.db import migrations
from events.models import Pipeline, Search

# Creates initial search pipeline instances

# List of search pipeline names
NEW_PIPELINES = [
    ('SVOM', Pipeline.PIPELINE_TYPE_EXTERNAL),
]

def add_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')
    Search = apps.get_model('events', 'Search')

    # Create pipelines
    for pipeline_name in NEW_PIPELINES:
        pipeline, created = Pipeline.objects.get_or_create(name=pipeline_name[0])
        pipeline.pipeline_type = pipeline_name[1]
        pipeline.save()

def remove_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')
    Search = apps.get_model('events', 'Search')

    # Delete pipelines
    for pipe in NEW_PIPELINES:
        Pipeline.objects.filter(name=pipe[0]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0089_alter_emobservation_group_and_more'),
    ]

    operations = [
        migrations.RunPython(add_pipelines, remove_pipelines),
    ]
