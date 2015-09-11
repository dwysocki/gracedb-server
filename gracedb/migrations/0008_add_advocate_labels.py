# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def add_advocate_labels(apps, schema_editor):
    Label = apps.get_model("gracedb", "Label")
    for name in ['ADVREQ', 'ADVOK', 'ADVNO']:
        Label.objects.create(name=name)

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0007_auto_new_signoff_model'),
    ]

    operations = [
        migrations.RunPython(add_advocate_labels),
    ]
