# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

# Request to update certificate from Meg Millhouse (7 Aug 2017)
ROBOT = {
    'username': 'gstlalcbc',
    'newcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=gstlalcbc/pcdev3.phys.uwm.edu',
}

def add_cert(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Create new cert
    newcert, c_created = X509Cert.objects.get_or_create(
        subject=ROBOT['newcert'])

    # Add new cert to user
    user = LocalUser.objects.get(username=ROBOT['username'])
    newcert.users.add(user)
    newcert.save()

    # Save user
    user.save()

def remove_cert(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Delete new cert.
    newcert = X509Cert.objects.get(subject=ROBOT['newcert'])
    newcert.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0020_update_bayeswave_robots'),
    ]

    operations = [
        migrations.RunPython(add_cert, remove_cert)
    ]

# End of file
