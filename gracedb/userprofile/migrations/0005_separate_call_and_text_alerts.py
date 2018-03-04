# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import userprofile.models


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0004_add_contact_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='call_phone',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contact',
            name='text_phone',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=userprofile.models.PhoneNumberField(blank=True, max_length=255, validators=[userprofile.models.validate_phone]),
        ),
    ]
