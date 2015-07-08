# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='ligoldapuser',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='localuser',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
