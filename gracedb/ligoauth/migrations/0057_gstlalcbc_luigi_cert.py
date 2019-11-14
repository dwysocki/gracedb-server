ngo 1.11.20 on 2019-06-03 20:10
from __future__ import unicode_literals

from django.db import migrations

# Note: the CN in the cert is for detchar-la, not detchar.

ACCOUNT = {
    'name': 'gstlalcbc',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=submit.nemo.uwm.edu/CN=gstlal_online_luigi/CN=Duncan Meacher/CN=UID:duncan.meacher.robot',
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
        ('ligoauth', '0056_update_dashboard_cert'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
