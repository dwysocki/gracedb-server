# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0025_add_label_descriptions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='label',
            name='description',
            field=models.TextField(),
        ),
    ]
