# -*- coding: utf-8 -*-
# Default imports
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings

ROBOTS = [{'username': {'old': 'LIB', 'new': 'LIB_PE'},
           'last_name': {'old': 'LIB at CIT', 'new': 'LIB PE at CIT'},
          },
          {'username': 'oLIB',
           'last_name': {'old': 'LIB at CIT', 'new': 'oLIB at CIT'},
          },
]

def create_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')

    # Get user and update information
    for entry in ROBOTS:
        update_username = False
        # get user
        if isinstance(entry['username'], dict):
            username = entry['username']['old']
            update_username = True
        else:
            username = entry['username']
        user = LocalUser.objects.get(username=username)

        # update information
        if update_username:
            user.username = entry['username']['new']
        user.last_name = entry['last_name']['new']

        # save
        user.save()

def delete_robots(apps, schema_editor):
    LocalUser = apps.get_model('ligoauth','LocalUser')

    # Get user and update information
    for entry in ROBOTS:
        update_username = False
        # get user
        if isinstance(entry['username'], dict):
            username = entry['username']['new']
            update_username = True
        else:
            username = entry['username']
        user = LocalUser.objects.get(username=username)

        # update information
        if update_username:
            user.username = entry['username']['old']
        user.last_name = entry['last_name']['old']

        # save
        user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('ligoauth', '0017_add_virgo_detchar'),
    ]

    operations = [
        migrations.RunPython(create_robots, delete_robots)
    ]

# End of file
