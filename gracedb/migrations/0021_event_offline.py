# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0020_fix_lib_perms'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='offline',
            field=models.BooleanField(default=False),
        ),
    ]
