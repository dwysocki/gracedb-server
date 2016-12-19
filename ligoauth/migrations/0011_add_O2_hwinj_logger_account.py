# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOT = {'username': 'hinj',
         'first_name': '',
         'last_name': 'HWINJ Monitor',
         'email': 'mhulko@caltech.edu',
         'is_active': True,
         'is_staff': False,
         'is_superuser': False
}
# Certificate for nagios user on gracedb.
CERT_SUBJ = '/DC=org/DC=ligo/O=LIGO/OU=Services/CN=hinj/ldas-grid.ligo.caltech.edu'

def create_robot(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')
    X509Cert = apps.get_model('ligoauth','X509Cert')
    Group = apps.get_model('auth','Group')
    Permission = apps.get_model('auth','Permission')

    lvc_group = Group.objects.get(name=settings.LVC_GROUP)
    add_event_perm = Permission.objects.get(codename='add_event')

    # get or create user
    user, created = LocalUser.objects.get_or_create(username=ROBOT['username'])
    if created:
        for key in ROBOT.keys():
            setattr(user, key, ROBOT[key])

    # Give user permission to add events
    if add_event_perm not in user.user_permissions.all():
        user.user_permissions.add(add_event_perm)

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

    # Delete user.
    LocalUser.objects.get(username=ROBOT['username']).delete()

    # Delete cert.
    X509Cert.objects.get(subject=CERT_SUBJ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0010_add_nagios_gracedb_robot_and_cert'),
    ]

    operations = [
        migrations.RunPython(create_robot, delete_robot)
    ]

# End of file
