# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gracedb', '0003_grbevent_trigger_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperatorSignoff',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instrument', models.CharField(max_length=2, choices=[(b'H1', b'LHO'), (b'L1', b'LLO'), (b'V1', b'Virgo')])),
                ('status', models.CharField(max_length=2, choices=[(b'OK', b'OKAY'), (b'NO', b'NOT OKAY')])),
                ('comment', models.TextField(blank=True)),
                ('event', models.ForeignKey(to='gracedb.Event')),
                ('submitter', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
