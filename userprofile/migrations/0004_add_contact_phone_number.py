# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import userprofile.models


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0003_trigger_label_query'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='phone',
            field=userprofile.models.PhoneNumberField(blank=True, max_length=255, validators=[userprofile.models.validate_phone, userprofile.models.validate_phone, userprofile.models.validate_phone]),
        ),
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(max_length=254, blank=True),
        ),
    ]
