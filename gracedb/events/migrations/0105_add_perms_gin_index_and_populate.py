# Migration to add GIN index on Event.perms field and populate it
from django.db import migrations
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
import json


def populate_event_perms(apps, schema_editor):
    """
    Populate the Event.perms field for all events that don't have it set.

    This denormalizes permission data from guardian tables into a JSON field
    on each event for fast permission filtering.
    """
    Event = apps.get_model('events', 'Event')
    GroupObjectPermission = apps.get_model('guardian', 'GroupObjectPermission')

    # Get the content type for Event
    try:
        content_type = ContentType.objects.get(app_label='events', model='event')
    except ContentType.DoesNotExist:
        # If content type doesn't exist yet, skip this migration
        return

    # Find events with null or empty perms
    events_to_update = Event.objects.filter(
        graceid__isnull=False
    ).filter(
        Q(perms__isnull=True) | Q(perms='')
    )

    print(f"\nPopulating perms for {events_to_update.count()} events...")

    batch_size = 1000
    updated_count = 0

    for event in events_to_update.iterator(chunk_size=batch_size):
        # Get all GroupObjectPermissions for this event
        group_object_perms = GroupObjectPermission.objects.filter(
            object_pk=str(event.id),
            content_type_id=content_type.id  # Use content_type_id instead of content_type
        ).select_related('group', 'permission')

        # Build permission strings
        perm_strings = []
        for gop in group_object_perms:
            perm_string = '{}_can_{}'.format(
                gop.group.name,
                gop.permission.codename.split('_')[0]
            )
            perm_strings.append(perm_string)

        # Update the event
        event.perms = json.dumps(perm_strings)
        event.save(update_fields=['perms'])

        updated_count += 1
        if updated_count % 1000 == 0:
            print(f"  Updated {updated_count} events...")

    print(f"Completed: Updated {updated_count} events total.")


def reverse_populate_perms(apps, schema_editor):
    """
    On rollback, clear the perms field (optional - could also leave as-is).
    """
    # We can just leave the perms field as-is on rollback
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0104_mlyburstevent_end_time_mlyburstevent_end_time_ns_and_more'),
    ]

    operations = [
        # Ensure pg_trgm extension is enabled (needed for trigram GIN index)
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="-- Extension pg_trgm not dropped on reverse"
        ),

        # Add GIN index on perms field for fast text search
        # GIN indexes are great for JSONB and text fields with contains queries
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS events_event_perms_gin_idx
                ON events_event USING gin (perms gin_trgm_ops);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS events_event_perms_gin_idx;
            """
        ),

        # Populate perms field for all events
        migrations.RunPython(
            populate_event_perms,
            reverse_populate_perms
        ),
    ]
