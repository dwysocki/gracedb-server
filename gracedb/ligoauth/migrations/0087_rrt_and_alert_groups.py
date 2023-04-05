# -*- coding: utf-8 -*-
# created by Alexander Pace, 2023-04-04
from __future__ import unicode_literals

from django.db import migrations

GROUP_DATA = { 'rrt_members' : {'description': 'Rapid Response Team (RRT) '
                                               'Members',
                                'ldap_group_names' : {'RRT, LVC':
                                                        'Services:GraceDB:PrivilegedGroups:RRT:authorized',
                                                      'RRT, KAGRA':
                                                        'gw-astronomy:KAGRA-LIGO:graceDB:privilegedGroups:RRT'}
                               },
               'priority_alerts': {'description': 'Priority Alert Members',
                                   'ldap_group_names' : {'Priority Alerts, LVC':
                                                         'Services:GraceDB:PrivilegedGroups:PriorityAlerts:authorized',
                                                         'Priority Alerts, KAGRA':
                                                         'gw-astronomy:KAGRA-LIGO:graceDB:privilegedGroups:PriorityAlerts'}
                                   }
               }

def create_ldapauthgroups(apps, schema_editor):
    DjangoGroup = apps.get_model('auth', 'Group')
    AuthGroup = apps.get_model('ligoauth', 'AuthGroup')
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    # Loop over new groups:
    for name in GROUP_DATA.keys():
        data = GROUP_DATA[name]
        # Create the Django group
        g, created = DjangoGroup.objects.get_or_create(name=name)

        # Create the AuthGroup:
        ag = AuthGroup(group_ptr=g)
        ag.description = data['description']

        # Update from base class
        ag.__dict__.update(g.__dict__)

        # Save AuthGroup
        ag.save()

        # Now loop over ldap_group_names to create new ALM's:

        for gname in data['ldap_group_names'].keys():
            alm, created = AuthorizedLdapMember.objects.get_or_create(name=gname)
            alm.ldap_gname = data['ldap_group_names'][gname]
            alm.ldap_authgroup = ag
            alm.save()

def delete_ldapauthgroups(apps, schema_editor):
    DjangoGroup = apps.get_model('auth', 'Group')
    AuthGroup = apps.get_model('ligoauth', 'AuthGroup')
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    # Loop over groups and delete Groups:
    for name in GROUP_DATA.keys():
        # Delete ALG's first:
        data = GROUP_DATA[name]
        for gname in data['ldap_group_names'].keys():
            alm = AuthorizedLdapMember.objects.get(name=gname)
            alm.delete()

        # Delete AuthGroup and djangogroup:
        ag = AuthGroup.objects.get(name=name)
        ag.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0086_hwinj_update'),
    ]

    operations = [
        migrations.RunPython(create_ldapauthgroups, delete_ldapauthgroups),
    ]
