# -*- coding: utf-8 -*-
# fixes:
# https://git.ligo.org/computing/helpdesk/-/issues/3852
from __future__ import unicode_literals

from django.db import migrations

ACCOUNT = {
    'name': 'waveburst',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=gaevirgo01.ciemat.es/CN=cwbonline-gaevirgo01/CN=Marco Drago/CN=UID:marco.drago.robot',
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
        ('ligoauth', '0093_230524_accounts'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
