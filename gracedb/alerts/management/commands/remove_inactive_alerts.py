import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from alerts.models import Contact, Trigger


class Command(BaseCommand):
    help="Delete Contacts and Notifications for inactive users"

    def add_arguments(self, parser):
        parser.add_argument('-q', '--quiet', action='store_true',
            default=False, help='Suppress output')

    def handle(self, *args, **options):
        verbose = not options['quiet']

        if verbose:
            self.stdout.write(('Checking inactive users\' triggers and '
                'contacts at {0}').format(datetime.datetime.utcnow()))

        # Get contacts and triggers whose user is no longer in the LVC
        lvc = Group.objects.get(name=settings.LVC_GROUP)
        triggers = Trigger.objects.exclude(user__groups=lvc)
        contacts = Contact.objects.exclude(user__groups=lvc)

        # Generate log message
        if verbose:
            if triggers.exists():
                t_log_msg = "Deleting {0} triggers: ".format(triggers.count())\
                    + " | ".join([t.__str__() for t in triggers])
                self.stdout.write(t_log_msg)
            if contacts.exists():
                c_log_msg = "Deleting {0} contacts: ".format(contacts.count())\
                     + " | ".join([c.__str__() for c in contacts])
                self.stdout.write(c_log_msg)

        # Delete
        triggers.delete()
        contacts.delete()
