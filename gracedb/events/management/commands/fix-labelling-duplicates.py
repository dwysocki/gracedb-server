from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from events.models import Event, Label, Labelling, EventLog
from superevents.models import Superevent

try:
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment("remove-test-events-segment")
except ModuleNotFoundError:
    print("aws_xray_sdk not found, skipping.")


log_message = 'Duplicate label <span style="color:{color};">{label_name}</span> was ' \
              'removed as part of regular database maintenance.'

robot_last_name = 'GraceDB'
robot_user_name = 'gracedb_robot'

class Command(BaseCommand):
    help= 'Searches for events that have duplicate labels, removes the label, ' \
          'and then writes a log message that the label was removed.'

    def add_arguments(self, parser):
        parser.add_argument('-q', '--dry-run', action='store_true',
            default=False, help='Don\'t actually delete labels.')

    def handle(self, *args, **options):

        # Get or create a "GraceDB" user (just to show up in log messages):
        gracedb_robot, created = User.objects.get_or_create(username=robot_user_name,
                                     last_name=robot_last_name)

        if created:
            print(f'created {robot_last_name} user for logging operations.')

        for lab in Label.objects.all():
            print(f'Looking for duplicate labels for {lab.name}')

            # The following query returns a queryset of value dictionaries that look
            # like:
            # {'event': integer row ID of event that has duplicate labels,
            #  'id__count': how many instances of repeated labels it has (usually 2)}

            repeats = Labelling.objects.filter(label=lab).values('event')\
                      .annotate(Count('id')).order_by().filter(id__count__gt=1)

            if repeats.exists():
                print(f'--> {repeats.count()} duplicate labels detected.')

                for rep in repeats:
                    # Get the event for the label duplication:
                    rep_event = Event.objects.get(id=rep['event'])

                    # Get the label objects:
                    rep_labels_for_event = Labelling.objects.filter(event=rep_event,
                                               label=lab)

                    # Make super sure that they're actually duplicates:
                    if rep_labels_for_event.count() > 1:

                        # Actually for real delete them.
                        if not options['dry_run']:
                            print(f'----> clearing duplicate labels for {rep_event.graceid}')
                            for label_to_delete in rep_labels_for_event[1:]:
                                print(f'----> writing a log messaage for {rep_event.graceid}')
                                msg =log_message.format(color=label_to_delete.label.defaultColor,
                                                        label_name=label_to_delete.label.name)
                                EventLog.objects.create(event=label_to_delete.event,
                                                        comment=msg,
                                                        issuer=gracedb_robot)
                                label_to_delete.delete()

                    else:
                        err_msg = (f'{lab.name} was determined to be a duplicate label for '
                                   f'{rep_event.graceid}, but something went wrong. Quitting.')
                        raise ValueError(err_msg)

            else:
                print(f'--> No duplicates found for label {lab.name}')
