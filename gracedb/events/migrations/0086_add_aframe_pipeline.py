# -*- coding: utf-8 -*-
# supports:
# https://git.ligo.org/computing/gracedb/server/-/issues/298

from __future__ import unicode_literals

from django.db import migrations
from events.models import Pipeline

# Creates initial search pipeline instances

# List of search pipeline names
NEW_PIPELINES = [
    ('aframe', Pipeline.PIPELINE_TYPE_SEARCH_PRODUCTION)
]

def add_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')

    # Create pipelines
    for pipeline_name in NEW_PIPELINES:
        pipeline, created = Pipeline.objects.get_or_create(name=pipeline_name[0])
        pipeline.pipeline_type = pipeline_name[1]
        pipeline.save()

def remove_pipelines(apps, schema_editor):
    Pipeline = apps.get_model('events', 'Pipeline')

    # Delete pipelines
    Pipeline.objects.filter(name__in=NEW_PIPELINES).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0085_add_detchar_group'),
    ]

    operations = [
        migrations.RunPython(add_pipelines, remove_pipelines),
    ]
