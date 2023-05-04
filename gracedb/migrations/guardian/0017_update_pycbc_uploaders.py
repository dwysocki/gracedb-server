# -*- coding: utf-8 -*-
# fixes:
# https://git.ligo.org/computing/gracedb/server/-/issues/287
from __future__ import unicode_literals

from django.db import migrations

# Creates UserObjectPermission objects which allow specific users
# to add events for pycbc. Also removes users that aren't in the 
# collaboration anymore. They couldn't log in and up

PIPELINE_NAME = 'pycbc'

USERS_TO_REMOVE = [
     'andrewlawrence.miller@ligo.org',
     'henning.fehrmann@ligo.org',
     'karsten.wiesner@ligo.org',
     'collin.capano@ligo.org',
     'alex.nitz@ligo.org',
     'christopher.biwer@ligo.org',
     'stanislav.babak@ligo.org',
     'gergely.debreczeni@ligo.org',
     'duncan.brown@ligo.org',
     'badri.krishnan@ligo.org',
     'saeed.mirshekari@ligo.org',
      ]

USERS_TO_ADD = [
     'max.trevor@ligo.org',
     'kanchan.soni@ligo.org',
     'shreejit.jadhav@ligo.org',
     'xan.morice-atkinson@ligo.org',
     'stephanie.hoang@ligo.org',
     'praveen.kumar@ligo.org',
     'ana.lorenzo@ligo.org',
     'adrianofrattale.mascioli@ligo.org',
     'barna.fekecs@ligo.org',
     'bhooshan.gadre@ligo.org',
      ]

def add_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    pipeline, created  = Pipeline.objects.get_or_create(name=PIPELINE_NAME)

    # First remove the old uploaders:
    for u in USERS_TO_REMOVE:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

        uop.delete()

    # Now add the new people:
    for u in USERS_TO_ADD:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

def remove_permissions(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    UserObjectPermission = apps.get_model('guardian', 'UserObjectPermission')
    Pipeline = apps.get_model('events', 'Pipeline')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    perm = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get_for_model(Pipeline)

    pipeline, created  = Pipeline.objects.get_or_create(name=PIPELINE_NAME)
    # first remove the new people:
    for u in USERS_TO_ADD:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

        uop.delete()

    # Put the old people back:
    for u in USERS_TO_REMOVE:
        # get the user object:
        user, _  = User.objects.get_or_create(username=u)

        # now get the corresponding userobjectpermission:
        uop, _ = UserObjectPermission.objects.get_or_create(
                user=user, permission=perm, content_type=ctype,
                object_pk=pipeline.id)

    pass

class Migration(migrations.Migration):

    dependencies = [
        ('guardian', '0016_emfollow_upload_mly'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
