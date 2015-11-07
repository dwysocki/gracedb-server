# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0002_auto_20150708_1134'),
    ]

    operations = [
        migrations.AddField(
            model_name='trigger',
            name='label_query',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
