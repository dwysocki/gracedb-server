# This migration changes the ldap group name from the old 'Communities..'
# semantics to the updated 'Services...'. Also fix a long-standing typo
# "AdvoVates"--> "AdvoCates" that was living in the source code forever.

from __future__ import unicode_literals

from django.db import migrations

GROUP_DATA = [
    {
        'name': 'EM Advocates',
        'old_ldap_gname': 'Communities:LVC:GraceDB:GraceDBAdvocates',
        'new_ldap_gname': 'Services:GraceDB:PrivilegedGroups:GraceDBAdvocates:authorized',
    },
]


def change_alm_groupname(apps, schema_editor):
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    # FixAuthrizedLdapMember community/service
    for group in GROUP_DATA:

        ema, created = AuthorizedLdapMember.objects.get_or_create(
                           ldap_gname=group['old_ldap_gname'])
        if not created:
            ema.name = group['name']
            ema.ldap_gname = group['new_ldap_gname']
            ema.save()


def change_back_alm_groupname(apps, schema_editor):
    AuthorizedLdapMember = apps.get_model('ligoauth', 'AuthorizedLdapMember')

    # FixAuthrizedLdapMember community/service
    for group in GROUP_DATA:

        ema, created = AuthorizedLdapMember.objects.get_or_create(
                           ldap_gname=group['new_ldap_gname'])
        if not created:
            ema.ldap_gname = group['old_ldap_gname']
            ema.save()


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0101_create_emfollow_devs_group'),
    ]

    operations = [
        migrations.RunPython(change_alm_groupname, change_back_alm_groupname),
    ]
