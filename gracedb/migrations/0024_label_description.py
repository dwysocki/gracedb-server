# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0023_add_DESGW_to_EMGroups'),
    ]

    operations = [
        migrations.AddField(
            model_name='label',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
