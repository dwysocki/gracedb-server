# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0017_add_virgo_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singleinspiral',
            name='channel',
            field=models.CharField(max_length=20, blank=True),
        ),
    ]
