from django.db import migrations



# This is a dictionary of pipeline uploaders for new scitoken
# robot accounts. the key: value structure is:
# pipeline name (str): [list of usernames (strs)]

P_UPLOADERS = {}

# this is a list of usernames for the various emfollow robot
# accounts. note to self: when the accounts get created, make a new
# migration (or edit this one) to change the last_name to
# "LIGO/Virgo EM Follow-Up", or "IGWN EM Follow-Up or something"

EMFOLLOW_ROBOTS = ['read-cvmfs-emfollow',
                   'read-cvmfs-emfollow-dev',
                   'read-cvmfs-emfollow-test',
                   'read-cvmfs-emfollow-playground',
    ]
SUPEREVENT_MANAGERS_GROUP = 'superevent_managers'
ACCESS_MANAGERS_GROUP = 'access_managers'
EM_ADVOCATES_GROUP = 'em_advocates'

# Many of these pipelines aren't used anymore and don't need to be
# uncommented. Note that emfollow_robots should still be given 
# upload permission for external pipelines so that RAVEN can upload
# external events.


## CWB2G
#P_UPLOADERS.update(
#    {'CWB2G': [
#        ]
#    }
#)


## gstlal
P_UPLOADERS.update(
    {'gstlal': [
        'alvin.li@shibbi.pki.itc.u-tokyo.ac.jp', # email, Re: IGWN Issuer Notes
        'gstlalcbc_online_cit-scitoken', # helpdesk 7352
        'gstlalcbc_online_uwm-scitoken', # helpdesk 7353
        'gstlalcbc_offline_psu-scitoken', # helpdesk 7354
        'gstlalcbc_offline_uwm-scitoken', # helpdesk 7355
        ]
    }
)


## spiir
P_UPLOADERS.update(
    {'spiir': [
        'spiir-low-latency-scitoken',
        ]
    }
)


## HardwareInjection
#P_UPLOADERS.update(
#    {'HardwareInjection': [
#        ]
#    }
#)


## X
#P_UPLOADERS.update(
#    {'X': [
#        ]
#    }
#)


## Q
#P_UPLOADERS.update(
#    {'Q': [
#        ]
#    }
#)


## Omega
#P_UPLOADERS.update(
#    {'Omega': [
#        ]
#    }
#)


## Ringdown
#P_UPLOADERS.update(
#    {'Ringdown': [
#        ]
#    }
#)


## Fermi
#P_UPLOADERS.update(
#    {'Fermi': [
#        ]
#    }
#)


## Swift
#P_UPLOADERS.update(
#    {'Swift': [
#        ]
#    }
#)


# CWB
P_UPLOADERS.update(
    {'CWB': [
        'cwbonlinecascina-scitoken',
        'cwbonline-scitoken',
        ]
    }
)


## SNEWS
#P_UPLOADERS.update(
#    {'SNEWS': [
#        ]
#    }
#)


## oLIB
#P_UPLOADERS.update(
#    {'oLIB': [
#        ]
#    }
#)


## pycbc
P_UPLOADERS.update(
    {'pycbc': [
        'pycbc-live', #https://git.ligo.org/computing/helpdesk/-/issues/7024
        'gareth.cabourndavies@ligo.org',
        'ian.harry@ligo.org',
        'max.trevor@ligo.org',
        'thomas.dent@ligo.org',
        ]
    }
)


## INTEGRAL
#P_UPLOADERS.update(
#    {'INTEGRAL': [
#        ]
#    }
#)


## AGILE
#P_UPLOADERS.update(
#    {'AGILE': [
#        ]
#    }
#)


# MLy
P_UPLOADERS.update(
    {'MLy': [ 'mly-pipeline-scitoken',
        ]
    }
)


## MBTAOnline
#P_UPLOADERS.update(
#    {'MBTAOnline': [
#        ]
#    }
#)


## MBTA
P_UPLOADERS.update(
    {'MBTA': [
        'mbta-scitoken',
        ]
    }
)


## aframe  # FIXME: aframe already has a scitoken credential
P_UPLOADERS.update(
    {'aframe': [
       'william.benoit@ligo.org',
       'ethan.marx@ligo.org',
        ]
    }
)


## SVOM
#P_UPLOADERS.update(
#    {'SVOM': [
#        ]
#    }
#)


## PyGRB
P_UPLOADERS.update(
    {'PyGRB': [ 'grb-exttrig-scitoken',
        ]
    }
)


## CHIME
#P_UPLOADERS.update(
#    {'CHIME': [
#        ]
#    }
#)


## IceCube
#P_UPLOADERS.update(
#    {'IceCube': [
#        ]
#    }
#)


## GWAK
#P_UPLOADERS.update(
#    {'GWAK': [
#        ]
#    }
#)


## SGNL
P_UPLOADERS.update(
    {'SGNL': [
       'sgnl-scitoken', #https://git.ligo.org/computing/helpdesk/-/issues/6964
       'sgnl-online-cit-scitoken',
       'sgnl-offline-cit-scitoken',
       'sgnl-offline-psu-scitoken',
       'yun-jing.huang@ligo.org',
       'chad.hanna@ligo.org',
       'emfollow',
        ]
    }
)


def add_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    success_string = 'Added {pline} permission for {username}'

    for pipeline_name, users in P_UPLOADERS.items():
        pipeline, created = Pipeline.objects.get_or_create(name=pipeline_name)

        # Loop over users
        for username in users:

            # get the user object
            user, _ = User.objects.get_or_create(username=username)

            # Create UserObjectPermission
            uop, uop_created = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

            print(success_string.format(pline=pipeline_name,
                                        username=username))

    # Now add the new emfollow accounts to the superevent_managers
    # group and access_managers group
    sm_group, _ = Group.objects.get_or_create(name=
                     SUPEREVENT_MANAGERS_GROUP)

    am_group, _ = Group.objects.get_or_create(name=
                     ACCESS_MANAGERS_GROUP)

    em_group, _ = Group.objects.get_or_create(name=
                     EM_ADVOCATES_GROUP)

    for emf in EMFOLLOW_ROBOTS:
        emfollow, _ = User.objects.get_or_create(username=emf)

        emfollow.groups.add(sm_group)
        emfollow.groups.add(am_group)
        emfollow.groups.add(em_group)

        print(f'Added {emf} to {SUPEREVENT_MANAGERS_GROUP}, {ACCESS_MANAGERS_GROUP},',
              f'{EM_ADVOCATES_GROUP}')


def remove_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    success_string = 'Removed {pline} permission for {username}'

    for pipeline_name, users in P_UPLOADERS.items():
        pipeline, created = Pipeline.objects.get_or_create(name=pipeline_name)

        # Loop over users
        for username in users:

            # get the user object
            user, _ = User.objects.get_or_create(username=username)

            # Remove UserObjectPermission
            uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

            uop.delete()

            print(success_string.format(pline=pipeline_name,
                                        username=username))

    # Now remove the new emfollow accounts from the superevent_managers
    # group.
    sm_group, _ = Group.objects.get_or_create(name=
                     SUPEREVENT_MANAGERS_GROUP)

    am_group, _ = Group.objects.get_or_create(name=
                     ACCESS_MANAGERS_GROUP)

    em_group, _ = Group.objects.get_or_create(name=
                     EM_ADVOCATES_GROUP)

    for emf in EMFOLLOW_ROBOTS:
        emfollow, _ = User.objects.get_or_create(username=emf)

        emfollow.groups.remove(sm_group)
        emfollow.groups.remove(am_group)
        emfollow.groups.remove(em_group)

        print(f'Removed {emf} from {SUPEREVENT_MANAGERS_GROUP}, {ACCESS_MANAGERS_GROUP}',
              f'{EM_ADVOCATES_GROUP}')


class Migration(migrations.Migration):

    dependencies = [
        ('guardian', '0026_update_gstlal_robots'),
        ('events', '0102_add_sgnl_pipeline'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
