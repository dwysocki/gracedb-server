# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOT = {
    'username': 'MbtaAlert',
    'newcert': '/C=IT/O=INFN/OU=Service/L=EGO/CN=MbtaAlert/olserver54.virgo.infn.it',
}

def create_cert(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Get user
    user = LocalUser.objects.get(username=ROBOT['username'])

    # create new certificate, add user
    cert = X509Cert.objects.create(subject=ROBOT['newcert'])
    cert.users.add(user)
    cert.save()

def delete_cert(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Get user
    user = LocalUser.objects.get(username=ROBOT['username'])

    # Remove new certificate
    cert = X509Cert.objects.get(subject=ROBOT['newcert'])
    cert.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0018_update_lib_accounts'),
    ]

    operations = [
        migrations.RunPython(create_cert, delete_cert)
    ]

# End of file
