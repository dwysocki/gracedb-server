# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0004_operatorsignoff'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='operatorsignoff',
            unique_together=set([('event', 'instrument')]),
        ),
    ]
