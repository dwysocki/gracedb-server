# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='grbevent',
            name='designation',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='grbevent',
            name='redshift',
            field=models.FloatField(null=True),
        ),
    ]
