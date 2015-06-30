# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gracedb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('desc', models.CharField(max_length=20)),
                ('email', models.EmailField(max_length=75)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Trigger',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('triggerType', models.CharField(blank=True, max_length=20, choices=[(b'create', b'create'), (b'change', b'change'), (b'label', b'label')])),
                ('farThresh', models.FloatField(null=True, blank=True)),
                ('contacts', models.ManyToManyField(to='userprofile.Contact', blank=True)),
                ('labels', models.ManyToManyField(to='gracedb.Label', blank=True)),
                ('pipelines', models.ManyToManyField(to='gracedb.Pipeline', blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
