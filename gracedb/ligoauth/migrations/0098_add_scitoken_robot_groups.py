# -*- coding: utf-8 -*-
# Generated on 2023-09-05
from __future__ import unicode_literals

from django.db import migrations

GROUP_DATA = [
    {
        'name': 'LVK SciToken Robots',
        'ldap_gname': 'Services:GraceDB:SciTokens:scopes:read:authorized',
    },
]


def create_ldapauthgroups(apps, schema_editor):
    AuthGroup = apps.get_model('ligoauth', 'AuthGroup')
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    internal_group = AuthGroup.objects.get(name='internal_users')

    # Create AuthrizedLdapMember instances
    for group in GROUP_DATA:

        lag = AuthorizedLdapMember.objects.create(
            name=group['name'],
            ldap_gname=group['ldap_gname'],
            ldap_authgroup=internal_group)
        lag.save()


def delete_ldapauthgroups(apps, schema_editor):
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    # Loop over groups and delete AuthGroup
    for group in GROUP_DATA:
        # Get AuthGroup
        group_name = group['name']
        ag = AuthorizedLdapMember.objects.get(name=group_name)

        # Delete AuthGroup and keep DjangoGroup base class
        ag.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0097_gstlalcbc_nemo'),
    ]

    operations = [
        migrations.RunPython(create_ldapauthgroups, delete_ldapauthgroups),
    ]
