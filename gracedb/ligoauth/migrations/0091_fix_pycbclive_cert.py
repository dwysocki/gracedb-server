# -*- coding: utf-8 -*-
# context: one of pycbclive's certs associated with tito's robot
# account was incorrectly in virgo_detchar's set. this migration
# checks for the existance of the cert, and if it isn't associated 
# with pycbclive, then move it. 

# https://git.ligo.org/computing/helpdesk/-/issues/3886

from __future__ import unicode_literals

from django.db import migrations

# first the subject of the cert in question:
subject = '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=ldas-grid.ligo.caltech.edu/CN=pycbclive/CN=Tito Canton/CN=UID:tito.canton.robot'

# the (true) owner's username:
username = 'pycbclive'

def add_cert(apps, schema_editor):
    RobotUser = apps.get_model('auth', 'User')
    X509Cert = apps.get_model('ligoauth', 'X509Cert')

    # Get the user 
    pycbclive = RobotUser.objects.get(username=username)

    # Get the cert:
    cert, created = X509Cert.objects.get_or_create(subject=subject)

    # Check the ownership of the cert, and if it's not pycbclive, then 
    # change and save:
    if cert.user != pycbclive:
        cert.user = pycbclive
        cert.save()


def delete_cert(apps, schema_editor):
    # nothing's going to break (ha!) by running this forward and backwards, so
    # just:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0090_add_cwb_cert'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
