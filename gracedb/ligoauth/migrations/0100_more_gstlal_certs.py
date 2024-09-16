# Edited manually to fix:
# https://git.ligo.org/computing/helpdesk/-/issues/6348#note_1077320

from __future__ import unicode_literals

from django.db import migrations

# Note: the CN in the cert is for detchar-la, not detchar.

ACCOUNTS = [
    {'name': 'gstlalcbc',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=gstlal.ligo.caltech.edu/CN=gstlalcbc_online/CN=Shomik Adhicary/CN=UID:shomik.adhicary.robot'},
    {'name': 'gstlalcbc_icds',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=comp-hd-001.gwave.ics.psu.edu/CN=gstlalcbc_icds/CN=Shomik Adhicary/CN=UID:shomik.adhicary.robot'},
]


def add_cert(apps, schema_editor):

    for ACCOUNT in ACCOUNTS:
        RobotUser = apps.get_model('auth', 'User')

        # Get user
        user = RobotUser.objects.get(username=ACCOUNT['name'])
    
        # Create new certificate
        user.x509cert_set.create(subject=ACCOUNT['new_cert'])


def delete_cert(apps, schema_editor):

    for ACCOUNT in ACCOUNTS:
        RobotUser = apps.get_model('auth', 'User')
    
        # Get user
        user = RobotUser.objects.get(username=ACCOUNT['name'])
    
        # Delete new certificate
        cert = user.x509cert_set.get(subject=ACCOUNT['new_cert'])
        cert.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0099_another_gwskynet_cert'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
