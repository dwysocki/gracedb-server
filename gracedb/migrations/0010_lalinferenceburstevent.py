# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0009_lengthen_emgroup_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='LalInferenceBurstEvent',
            fields=[
                ('event_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='gracedb.Event')),
                ('bci', models.FloatField(null=True)),
                ('quality', models.FloatField(null=True)),
                ('bsn', models.FloatField(null=True)),
                ('omicron_snr', models.FloatField(null=True)),
                ('hrss', models.FloatField(null=True)),
                ('frequency', models.FloatField(null=True)),
            ],
            bases=('gracedb.event',),
        ),
    ]
