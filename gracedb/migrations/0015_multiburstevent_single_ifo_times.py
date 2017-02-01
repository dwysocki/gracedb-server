# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0014_add_many_MOU_EMGroups'),
    ]

    operations = [
        migrations.AddField(
            model_name='multiburstevent',
            name='single_ifo_times',
            field=models.CharField(default=b'', max_length=255),
        ),
    ]
