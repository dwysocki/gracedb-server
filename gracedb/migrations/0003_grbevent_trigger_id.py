# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0002_auto_20150708_1140'),
    ]

    operations = [
        migrations.AddField(
            model_name='grbevent',
            name='trigger_id',
            field=models.CharField(max_length=25, null=True),
        ),
    ]
