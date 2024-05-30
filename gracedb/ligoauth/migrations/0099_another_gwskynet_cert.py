# Adding another cert for gwskynet:
# https://git.ligo.org/computing/helpdesk/-/issues/5958

from django.db import migrations

ACCOUNT = {
    'name': 'gwskynet',
    'new_cert': '/DC=org/DC=cilogon/C=US/O=LIGO/OU=Robots/CN=gracedb-playground.ligo.org/CN=GWSkyNet1/CN=Manleong Chan/CN=UID:manleong.chan.robot',
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
        ('ligoauth', '0098_add_scitoken_robot_groups'),
    ]

    operations = [
        migrations.RunPython(add_cert, delete_cert),
    ]
