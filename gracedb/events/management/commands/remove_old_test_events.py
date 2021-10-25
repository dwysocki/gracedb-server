from datetime import timedelta

from django.utils.timezone import now 
from django.core.management.base import BaseCommand
from events.models import Event, Group
from superevents.models import Superevent


class Command(BaseCommand):
    help="Remove test superevents and events older than three weeks."

    def handle(self, *args, **options):

        days_old = 21
    
        # Get lists of test superevents and events older than 21 days. 
        test_group = Group.objects.get(name='Test')
    
        t_now = now()
        date_cutoff = t_now - timedelta(days=days_old)
        superevent_list = Superevent.objects.filter(created__lt=date_cutoff,
                                                    category="T")
        event_list = Event.objects.filter(created__lt=date_cutoff,
                                          group=test_group)
    
        # Loop over superevents and delete
        print("Deleting {0} test superevents older than {1} days"
                "({2})".format(superevent_list.count(), days_old, t_now))
        for s in superevent_list:
            print("\tDeleting superevent {0}".format(s.superevent_id))
        
            # Delete superevent, removing its data and GroupObjectPermissions
            s.delete(purge=True)
    
        # Loop over events and delete
        print("Deleting {0} test events older than {1} days"
                "({2})".format(event_list.count(), days_old, t_now))
        for event in event_list:
            print("\tDeleting event {0}".format(event.graceid))
        
            # Delete event, removing data, subclasses, and GroupObjectPermissions
            # for the event and its subclasses
            event.delete(purge=True)

