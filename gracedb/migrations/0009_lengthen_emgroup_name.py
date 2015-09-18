# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0008_add_advocate_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emgroup',
            name='name',
            field=models.CharField(unique=True, max_length=50),
        ),
    ]
