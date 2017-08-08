# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

# Request to update certificate from Meg Millhouse (7 Aug 2017)
UPDATE_ROBOT = {
    'username': 'bayeswave',
    'newcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=bw_online/ldas-grid.ligo.caltech.edu',
    'oldcert': [
        '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=bayeswave_online/ldas-grid.ligo.caltech.edu',
    ],
}

def update_certs(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Create new cert
    newcert, c_created = X509Cert.objects.get_or_create(
        subject=UPDATE_ROBOT['newcert'])

    # Add new cert to bayeswave user
    bw_user = LocalUser.objects.get(username=UPDATE_ROBOT['username'])
    newcert.users.add(bw_user)
    newcert.save()

    # delete old certs
    for oc in UPDATE_ROBOT['oldcert']:
        oldcert = X509Cert.objects.get(subject=oc)
        oldcert.delete() 

    # Save user
    bw_user.save()

def revert_certs(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Delete new cert.
    newcert = X509Cert.objects.get(subject=UPDATE_ROBOT['newcert'])
    newcert.delete()

    # Create old certs and add user
    bw_user = LocalUser.objects.get(username=UPDATE_ROBOT['username'])
    for oc in UPDATE_ROBOT['oldcert']:
        oldcert, created = X509Cert.objects.get_or_create(subject=oc)
        oldcert.users.add(bw_user)
        oldcert.save()

    # Save user
    bw_user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0019_add_mbta_cert'),
    ]

    operations = [
        migrations.RunPython(update_certs, revert_certs)
    ]

# End of file
