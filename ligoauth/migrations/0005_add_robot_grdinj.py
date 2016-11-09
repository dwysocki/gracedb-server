# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

ROBOTS = [
        {
            'username' : 'GRD_INJ',
            'first_name' : '',
            'last_name' : 'GRD Injection',  # Note that the last_name acts as a display
            'email' : 'cmbiwer@syr.edu',
            'dns' : [
                "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=GRD_INJ/h1guardian0.cds.ligo-wa.caltech.edu",
            ]
        },
]

def create_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth', 'LocalUser')
    X509Cert = apps.get_model('ligoauth', 'X509Cert')
    Group = apps.get_model('auth', 'Group')
    lvc_group = Group.objects.get(name=settings.LVC_GROUP)

    for entry in ROBOTS:
        user, created = LocalUser.objects.get_or_create(username=entry['username'])
        if created:
            user.first_name = entry['first_name']
            user.last_name = entry['last_name']
            user.email = entry['email']
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.save()

        # Create the cert objects and link them to our user.
        for dn in entry['dns']:
            cert, created = X509Cert.objects.get_or_create(subject=dn)
            if created:
                cert.save()
            cert.users.add(user)

        # Add our user to the LVC group. This permission is required to
        # do most things, but may *NOT* always be appropriate. It may
        # also be necessary to give the robotic user permission to populate
        # a particular pipeline.
        lvc_group.user_set.add(user)
        print "Added User GRD_INJ"

def delete_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth', 'LocalUser')
    X509Cert = apps.get_model('ligoauth', 'X509Cert')

    for entry in ROBOTS:
        for dn in entry['dns']:
            X509Cert.objects.get(subject=dn).delete()
        LocalUser.objects.get(username=entry['username']).delete()



class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0004_add_grdinj'),
    ]

    operations = [
        migrations.RunPython(create_robots)
    ]
