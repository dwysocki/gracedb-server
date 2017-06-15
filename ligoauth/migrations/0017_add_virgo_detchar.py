# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOT = {'username': 'virgo_detchar',
         'first_name': '',
         'last_name': 'Virgo Detchar',
         'email': 'leroy@lal.in2p3.fr',
         'is_active': True,
         'is_staff': False,
         'is_superuser': False
}

# Certificate for nagios user on gracedb.
CERT_SUBJ = '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=Virgodetchar/lscgw.virgo.infn.it'

def create_robot(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')
    Group = apps.get_model('auth','Group')

    lvc_group = Group.objects.get(name=settings.LVC_GROUP)

    # get or create user
    user, created = LocalUser.objects.get_or_create(username=ROBOT['username'])
    if created:
        for key in ROBOT.keys():
            setattr(user, key, ROBOT[key])

    # Save user
    user.save()

    # Add user to LVC group.
    if not lvc_group in user.groups.all():
        lvc_group.user_set.add(user)
        lvc_group.save()

    # get or create certificate, add user
    cert, c_created = X509Cert.objects.get_or_create(subject=CERT_SUBJ)
    cert.users.add(user)
    cert.save()

def delete_robot(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')

    # Get user
    user = LocalUser.objects.get(username=ROBOT['username'])

    # Delete user.
    user.delete() 

    # Delete cert.
    X509Cert.objects.get(subject=CERT_SUBJ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0016_add_losc_account'),
    ]

    operations = [
        migrations.RunPython(create_robot, delete_robot)
    ]

# End of file
