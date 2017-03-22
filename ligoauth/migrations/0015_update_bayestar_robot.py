# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOTS = [{'username': 'bayestar-mic',
           'newcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=Online_CBC_BAYESTAR_O3_Preview/node746.cluster.ldas.cit',
           'oldcert': '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=bayestar-mic/node529.cluster.ldas.cit',
           'newemail': 'leo.singer@ligo.org',
           'oldemail': 'lsinger@caltech.edu',
          },
]

def create_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Get/create new user, get/create new cert, associate user with cert.
    for entry in ROBOTS:
        # get user, update email
        user = LocalUser.objects.get(username=entry['username'])
        user.email = entry['newemail']
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

    for entry in ROBOTS:
        # revert email
        user = LocalUser.objects.get(username=entry['username'])
        user.email = entry['oldemail']
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
        ('ligoauth', '0014_update_lib_robot'),
    ]

    operations = [
        migrations.RunPython(create_robots, delete_robots)
    ]

# End of file
