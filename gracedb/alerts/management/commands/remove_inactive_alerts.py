import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from alerts.models import Contact, Notification

# Turn on x-ray tracing for improved performance in AWS
try:
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment("remove-alerts-segment")
except ModuleNotFoundError:
    print("aws_xray_sdk not found, skipping.")


class Command(BaseCommand):
    help="Delete Contacts and Notifications for inactive users"

    def add_arguments(self, parser):
        parser.add_argument('-q', '--quiet', action='store_true',
            default=False, help='Suppress output')

    def handle(self, *args, **options):
        verbose = not options['quiet']

        if verbose:
            self.stdout.write(('Checking inactive users\' notifications and '
                'contacts at {0}').format(datetime.datetime.utcnow()))

        # Get contacts and notifications whose user is no longer in the LVC
        lvc = Group.objects.get(name=settings.LVC_GROUP)
        notifications = Notification.objects.exclude(user__groups=lvc)
        contacts = Contact.objects.exclude(user__groups=lvc)

        # Generate log message
        if verbose:
            if notifications.exists():
                t_log_msg = "Deleting {0} notifications: ".format(
                    notifications.count()) + " | ".join([t.__str__()
                    for t in notifications])
                self.stdout.write(t_log_msg)
            if contacts.exists():
                c_log_msg = "Deleting {0} contacts: ".format(contacts.count())\
                     + " | ".join([c.__str__() for c in contacts])
                self.stdout.write(c_log_msg)

        # Delete
        notifications.delete()
        contacts.delete()
