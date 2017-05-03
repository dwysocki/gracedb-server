# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.contrib.auth.models import Permission, ContentType

# permission objects which should be removed
perm_code = u'view_lalinferenceburstevent'
BAD_PERMS = [
    {
        'ct_model': 'event',
    },
    {
        'ct_model': 'pipeline',
    },
]
    

def fix_perms(apps, schema_editor):

    # Get relevant permission objects
    perms = Permission.objects.filter(codename=perm_code)

    # loop over perms and delete the non-relevant ones
    for p in perms:
        if p.content_type.model != 'lalinferenceburstevent':
            p.delete()
            print "\nDeleted {0}".format(p.content_type.name)

def unfix_perms(apps, schema_editor):
    # re-add the bad permissions
    for b in BAD_PERMS:
        ctype = ContentType.objects.get(model=b['ct_model'])
        p, created = Permission.objects.get_or_create(codename=perm_code,
            content_type=ctype, name=u'Can view lalinferenceburstevent')
        if created:
            print "\nCreated permission for {0}".format(b['ct_model'])
            p.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gracedb', '0019_fix_CTA_MOU_group'),
    ]

    operations = [
        migrations.RunPython(fix_perms, unfix_perms),
    ]
