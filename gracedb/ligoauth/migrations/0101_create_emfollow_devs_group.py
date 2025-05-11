from django.db import migrations


GROUP_DATA = {
        'name': 'emfollow_devs',
        'description': ('EMFollow Developers who require pipeline upload permission.'),
    }

MEMBERS = ['cody.messick@ligo.org',
           'deep.chatterjee@ligo.org',
           'geoffrey.mo@ligo.org',
           'sushant.sharma-chaudhary@ligo.org',
           'meg-scitoken',
]


def create_authgroups(apps, schema_editor):
    DjangoGroup = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    AuthGroup = apps.get_model('ligoauth', 'AuthGroup')

    # Create AuthGroup instances
    g, created = DjangoGroup.objects.get_or_create(name=GROUP_DATA['name'])
    ag = AuthGroup(group_ptr=g)
    ag.description = GROUP_DATA['description']

    # Update from base class
    ag.__dict__.update(g.__dict__)

    # Save
    ag.save()

    # Get initial set of members and add to the group. Have to
    # use a get_or_create here instead of a filter since we're
    # in a migration.
    for m in MEMBERS:
        u, created = User.objects.get_or_create(username=m)
        g.user_set.add(u)


def delete_authgroups(apps, schema_editor):
    AuthGroup = apps.get_model('ligoauth', 'AuthGroup')

    # Loop over groups and delete AuthGroup
    # Get AuthGroup
    group_name = GROUP_DATA['name']
    ag = AuthGroup.objects.get(name=group_name)

    # Delete AuthGroup and keep DjangoGroup base class
    ag.delete(keep_parents=True)


class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0100_more_gstlal_certs'),
    ]

    operations = [
        migrations.RunPython(create_authgroups, delete_authgroups),
    ]
