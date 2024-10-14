from django.db import models, migrations

# Add a migration to create the MOCK label. 
# That would indicate an event created by MEG (mock-event-generator)

# Label names, default colors, and descriptions
LABELS = [
    {'name': 'MOCK', 'defaultColor': 'blue', 'description': 'Mocked event/superevent created by the mock-event-generator.'},
]

def add_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Create labels
    for label_dict in LABELS:
        l, created = Label.objects.get_or_create(name=label_dict['name'])
        if created:
            l.defaultColor = label_dict['defaultColor']
            l.description = label_dict['description']
            l.save()
        else:
            print("label exists in database, moving on")

def remove_labels(apps, schema_editor):
    Label = apps.get_model('events', 'Label')

    # Delete labels
    Label.objects.filter(name__in=[l['name'] for l in LABELS]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0098_mlyburstevent_channel')
    ]

    operations = [
        migrations.RunPython(add_labels, remove_labels)
    ]
