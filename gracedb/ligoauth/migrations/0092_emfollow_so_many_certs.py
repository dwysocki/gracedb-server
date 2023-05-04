# -*- coding: utf-8 -*-
# Step 1 in transferring certificate ownership from leo singer to 
# cody messick: add cody's, and once they're in place, satya will 
# transfer ownership and then i'll remove leo's.
#
# reference: https://git.ligo.org/computing/helpdesk/-/issues/3702

from __future__ import unicode_literals

from django.db import migrations

# detchar is on a tear getting new certs, so I'm doing three
# at once.

gracedb_account = 'emfollow'

new_certs = [
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow-playground.ligo.caltech.edu/CN=emfollow-playground/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo-la.caltech.edu/CN=emfollow-playground-la/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo-wa.caltech.edu/CN=emfollow-playground-wa/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo.caltech.edu/CN=emfollow-playground/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo-wa.caltech.edu/CN=emfollow-wa/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo.caltech.edu/CN=emfollow/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow.ligo-la.caltech.edu/CN=emfollow-la/CN=Cody Messick/CN=UID:cody.messick.robot',
      '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=emfollow-test.ligo.caltech.edu/CN=emfollow-test/CN=Cody Messick/CN=UID:cody.messick.robot',
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
        ('ligoauth', '0091_fix_pycbclive_cert'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
