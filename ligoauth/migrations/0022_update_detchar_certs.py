# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

# Request to update certificate from Meg Millhouse (7 Aug 2017)
ROBOT = {
    'username': 'detchar',
    'newcerts': [
        '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=detchar/detchar.ligo.caltech.edu',
        '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=detchar/dcs.ligo-wa.caltech.edu',
        ],
    'oldcerts': [
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo-la.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev4.ligo.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev1.ligo-wa.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo-wa.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo-la.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo-la.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev2.ligo.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-pcdev3.ligo.caltech.edu',
        '/DC=org/DC=doegrids/OU=Services/CN=detchar/ldas-grid.ligo-wa.caltech.edu',
        '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=detchar/ldas-pcdev1.ligo.caltech.edu',
        '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=detchar/ldas-pcdev1.ligo-wa.caltech.edu',
        ],
}

def update_certs(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Create new certs
    user = LocalUser.objects.get(username=ROBOT['username'])
    for cert in ROBOT['newcerts']:
        newcert, c_created = X509Cert.objects.get_or_create(
            subject=cert)

        # Add new cert to user
        newcert.users.add(user)
        newcert.save()

    # Save user
    user.save()

    # Remove old certs
    for cert in ROBOT['oldcerts']:
        oldcert = X509Cert.objects.get(subject=cert)
        oldcert.delete()

def revert_certs(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Delete new certs.
    for cert in ROBOT['newcerts']:
        newcert = X509Cert.objects.get(subject=cert)
        newcert.delete()

    # Create old certs
    user = LocalUser.objects.get(username=ROBOT['username'])
    for cert in ROBOT['oldcerts']:
        oldcert, created = X509Cert.objects.get_or_create(subject=cert)

        # Add to user
        oldcert.users.add(user)
        oldcert.save()

    # Save user
    user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0021_gstlal_UWM_cert'),
    ]

    operations = [
        migrations.RunPython(update_certs, revert_certs)
    ]

# End of file
