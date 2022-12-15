# -*- coding: utf-8 -*-
# Homemade and handcrafted on 2022-12-08
from __future__ import unicode_literals

from django.db import migrations

gracedb_account = 'spiir'
new_certs = ['/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=spiir.ligo.caltech.edu/CN=spiir-spiir/CN=Luke Davis/CN=UID:luke.davis.robot',
            ]


def add_cert(apps, schema_editor):
    RobotUser = apps.get_model('auth', 'User')

    # Get user
    user = RobotUser.objects.get(username=gracedb_account)

    # Create new certificates
    for cert in new_certs:
        user.x509cert_set.create(subject=cert)


def delete_cert(apps, schema_editor):
    RobotUser = apps.get_model('auth', 'User')

    # Get user
    user = RobotUser.objects.get(username=gracedb_account)

    # Delete new certificates
    for cert in new_certs:
      cert = user.x509cert_set.get(subject=cert)
      cert.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0082_add_new_robot_certs'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
