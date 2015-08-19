# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

users = [
        {
            'username' : 'TIGER',
            'first_name' : '',
            'last_name' : 'TIGER',
            'email' : 'salvatore.vitale@ligo.org',
            'dns' : [
                "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=TIGER/ldas-pcdev1.ligo.caltech.edu",
            ]
        },
]

def add_robot_user(apps, schema_editor):
    X509Cert = apps.get_model("ligoauth", "X509Cert")
    LocalUser = apps.get_model("ligoauth", "LocalUser")

    for entry in users:
        user, created = LocalUser.objects.get_or_create(username=entry['username'])
        if created:
            user.first_name = entry['first_name']
            user.last_name = entry['last_name']
            user.email = entry['email']
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.save()
        current_dns = set([cert.subject for cert in user.x509cert_set.all()])
        new_dns = set(entry['dns'])

        missing_dns = new_dns - current_dns
        redundant_dns = current_dns - new_dns

        for dn in missing_dns:
            cert, created = X509Cert.objects.get_or_create(subject=dn)
            if created:
                cert.save()
            cert.users.add(user)

        for dn in redundant_dns:
            cert = X509Cert.objects.get(subject=dn)
            cert.users.remove(user)

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0002_auto_20150708_1134'),
    ]

    operations = [
        migrations.RunPython(add_robot_user),
    ]
