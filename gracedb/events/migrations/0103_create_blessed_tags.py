from django.db import migrations

# Create a blessed tag for RAVEN:
# https://git.ligo.org/computing/gracedb/server/-/issues/368
# and for cgmi

# List of tag names and display names
BLESSED_TAGS = [
    {'name': 'raven_report', 'displayName': 'RAVEN Report'},
    {'name': 'cgmi', 'displayName': 'Coarse-Grained Mass Information'},
]

def add_tags(apps, schema_editor):
    Tag = apps.get_model('events', 'Tag')

    # Create tags
    for tag_dict in BLESSED_TAGS:
        tag, created = Tag.objects.get_or_create(name=tag_dict['name'])
        if created:
            tag.displayName = tag_dict['displayName']
            tag.save()

def remove_tags(apps, schema_editor):
    Tag = apps.get_model('events', 'Tag')

    # Delete tags
    Tag.objects.filter(name__in=[s['name'] for s in BLESSED_TAGS]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0102_add_sgnl_pipeline'),
    ]

    operations = [
        migrations.RunPython(add_tags, remove_tags),
    ]
