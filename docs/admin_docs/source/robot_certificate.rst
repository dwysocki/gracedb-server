.. _robot_certificate:

================================
Creating a robot account
================================

General information on robot accounts
=====================================

The flagship data analysis pipelines are usually operated by groups of 
users. Thus, it doesn't make much sense for the events to be submitted to GraceDB
via a single user's account. This is also impractical, as an individual
user's auth tokens expire often, but the pipeline process needs to be running
all the time. 

Thus, some kind of persistent auth token is required, and this should be
attached to a GraceDB account that is *not* an individual user's personal
account. That way, a user running the data analysis pipeline can also 
comment on the event as him or herself, and the provenance information is 
clear and consistent. Robot accounts are thus, in effect, shared accounts.

Robot authentication
====================

At present, most robots authenticate to GraceDB using x509 certificates.
Users are discouraged from moving cert/key pars around from machine to machine,
so the usual recommendation is to ask that the person in charge of the robotic
process(es) obtain a cert/key pair for each computing cluster as needed. 
The Common Names will hopefully follow a sensible pattern::

    RobotName/ldas-pcdev1.ligo.caltech.edu
    RobotName/ldas-pcdev1.ligo-la.caltech.edu
    RobotName/ldas-pcdev1.ligo-wa.caltech.edu
    ...

Instructions for obtaining LIGO CA robot certificates can be found 
`here <https://wiki.ligo.org/AuthProject/LIGOCARobotCertificate>`__.

.. NOTE::
    LIGO CA robot certs expire after 1 year. The best way of "renewing"
    is to generate a new Certificate Signing Request (CSR) with the old key, and
    send that CSR to ``rt-auth``::

        openssl x509 -x509toreq -in currentcert.pem -out robot_cert_req.pem -signkey currentkey.pem

.. NOTE::
    Neither Apache nor the GraceDB app will check that the domain name
    in the user's cert DN resolves to the IP from which the user is connecting.
    (This is in contrast with the latest Globus tools, which do perform this
    check.) Thus, a user may connect from ``ldas-pcdev2`` at CIT, even if the CN
    in the cert is ``RobotName/ldas-pcdev1.ligo.caltech.edu``.

Once the user has obtained the certificates, ask him/her to send you the output
of::

    openssl x509 -subject -noout -in /path/to/robot_cert_file.pem

That way you will know the subject(s) to link with the robotic user when
you create it.

In the future, it is hoped that robots will authenticate using Shibboleth
rather than x509. The user would request a robotic keytab and this robotic
user would have the correct group memberships in the LDAP. This will all you
to eliminate the x509 authentication path in GraceDB altogether. See the
sketch at :ref:`shibbolized_client`.

Creating the robot user
=======================

These same steps could all be done by hand using the Django console. 
However, using a migration is encouraged since there is more of a paper trail
that way. See the Django docs on data migrations.

Create an empty data migration::

    python manage.py makemigrations --empty ligoauth

Rename the resulting file to something sane::

    cd ligoauth/migrations
    mv 0004_auto_20160229_1541.py 0004_add_robot_RobotName.py

Edit the migration to do what you want it to do. You could use this as a template::

    # -*- coding: utf-8 -*-
    from __future__ import unicode_literals

    from django.db import migrations, models
    from django.conf import settings

    ROBOTS = [
            {
                'username' : 'NewRobot',
                'first_name' : '',
                'last_name' : 'My New Robot',  # Note that the last_name acts as a display
                'email' : 'albert.einstein@ligo.org',
                'dns' : [
                    "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=NewRobot/ldas-pcdev1.ligo.caltech.edu.edu",
                    "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=NewRobot/ldas-pcdev1.ligo-la.caltech.edu.edu",
                    "/DC=org/DC=ligo/O=LIGO/OU=Services/CN=NewRobot/ldas-pcdev1.ligo-wa.caltech.edu.edu",
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

    def delete_robots(apps, schema_editor):
        LocalUser = apps.get_model('ligoauth', 'LocalUser')
        X509Cert = apps.get_model('ligoauth', 'X509Cert')

        for entry in ROBOTS:
            for dn in entry['dns']:
                X509Cert.objects.get(subject=dn).delete()
            LocalUser.objects.get(username=entry['username']).delete()

    class Migration(migrations.Migration):

        dependencies = [
            ('ligoauth', '0003_auto_20150819_1201'),
        ]

        operations = [
            migrations.RunPython(create_robots, delete_robots),
        ]
              

The above could definitely be refactored in some nice way.
I'll leave that as an exercise for the reader :-).
Now apply the migration::
    
    python manage.py migrate ligoauth
    


