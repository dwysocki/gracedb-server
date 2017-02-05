# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOTS = [{'username': 'LIB',
           'newcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=LIB/ldas-pcdev5.ligo.caltech.edu',
           'oldcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=LIB/ldas-pcdev1.ligo.caltech.edu'
          },
]

def create_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Get/create new user, get/create new cert, associate user with cert.
    for entry in ROBOTS:
        # get user
        user = LocalUser.objects.get(username=entry['username'])
        user.save()

        # get or create certificate, add user
        cert, c_created = X509Cert.objects.get_or_create(subject=entry['newcert'])
        cert.users.add(user)
        cert.save()

        # Delete old certs.
        try:
            cert = X509Cert.objects.get(subject=entry['oldcert'])
            cert.delete()
        except:
            pass

def delete_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Delete users.
    for entry in ROBOTS:
        user = LocalUser.objects.get(username=entry['username'])
        user.save()

        # Create oldcerts, add to user
        cert, created = X509Cert.objects.get_or_create(subject=entry['oldcert'])
        cert.users.add(user)
        cert.save()

        # Delete newcert.
        try:
            X509Cert.objects.get(subject=entry['newcert']).delete()
        except:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0013_update_bayeswave_robot'),
    ]

    operations = [
        migrations.RunPython(create_robots, delete_robots)
    ]

# End of file
