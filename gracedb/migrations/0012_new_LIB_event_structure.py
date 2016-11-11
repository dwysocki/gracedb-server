# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0011_add_AllSkyLong_search'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lalinferenceburstevent',
            old_name='frequency',
            new_name='frequency_mean',
        ),
        migrations.RenameField(
            model_name='lalinferenceburstevent',
            old_name='hrss',
            new_name='hrss_mean',
        ),
        migrations.RenameField(
            model_name='lalinferenceburstevent',
            old_name='omicron_snr',
            new_name='omicron_snr_network',
        ),
        migrations.RenameField(
            model_name='lalinferenceburstevent',
            old_name='quality',
            new_name='quality_mean',
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='frequency_median',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='hrss_median',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='omicron_snr_H1',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='omicron_snr_L1',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='omicron_snr_V1',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='lalinferenceburstevent',
            name='quality_median',
            field=models.FloatField(null=True),
        ),
    ]
