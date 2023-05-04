# -*- coding: utf-8 -*-
# fixes:
# https://git.ligo.org/computing/helpdesk/-/issues/3852
from __future__ import unicode_literals

from django.db import migrations

# Note: the CN in the cert is for detchar-la, not detchar.

ACCOUNT = {
    'name': 'waveburst',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=ligo.caltech.edu/CN=waveburst.online/CN=Marek Szczepanczyk/CN=UID:marek.szczepanczyk.robot',
}


def add_cert(apps, schema_editor):
    RobotUser = apps.get_model('auth', 'User')

    # Get user
    user = RobotUser.objects.get(username=ACCOUNT['name'])

    # Create new certificate
    user.x509cert_set.create(subject=ACCOUNT['new_cert'])


def delete_cert(apps, schema_editor):
    RobotUser = apps.get_model('auth', 'User')

    # Get user
    user = RobotUser.objects.get(username=ACCOUNT['name'])

    # Delete new certificate
    cert = user.x509cert_set.get(subject=ACCOUNT['new_cert'])
    cert.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0089_yet_another_gstlalcbc_cert'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
