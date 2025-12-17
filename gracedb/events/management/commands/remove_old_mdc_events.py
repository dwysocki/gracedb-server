from datetime import timedelta
import os
import humanize
from django.utils.timezone import now
from django.conf import settings
from django.core.management.base import BaseCommand
from events.models import Event
from superevents.models import Superevent

MDC_DAYS = settings.MDC_RETENTION_DAYS

class Command(BaseCommand):
    help = f'Remove MDC superevents and events older than a specified number of days (default={MDC_DAYS}). Calculates and displays total storage used before deletion.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=MDC_DAYS, help=f'Delete MDC events/superevents older than this many days (default: {MDC_DAYS})')
        parser.add_argument('--delete', action='store_true', help='Actually delete the MDC events/superevents. If not specified, only a dry run is performed.')
        parser.add_argument('--tally', action='store_true', help='Do a tally of storage to be cleared. Memory use may exceed capacity for small systems and large tallies.')

    def handle(self, *args, **options):
        days_old = options['days']
        do_delete = options['delete']
        do_tally = options['tally']
        t_now = now()
        date_cutoff = t_now - timedelta(days=days_old)

        # Find MDC superevents
        superevent_list = Superevent.objects.filter(created__lt=date_cutoff, category=Superevent.SUPEREVENT_CATEGORY_MDC)
        # Find MDC events
        event_list = Event.objects.filter(created__lt=date_cutoff, search__name='MDC').exclude(group__name='Test')

        # Gather datadirs
        superevent_dirs = [s.datadir for s in superevent_list]
        event_dirs = [e.datadir for e in event_list]
        all_dirs = superevent_dirs + event_dirs

        # Calculate total size
        def get_dir_size(path):
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total += os.path.getsize(fp)
            return total

        if do_tally:
            total_bytes = sum(get_dir_size(d) for d in all_dirs if os.path.isdir(d))
            total_human = humanize.naturalsize(total_bytes)
        else:
            total_human = "uncalculated"

        self.stdout.write(f"Clearing {superevent_list.count()} MDC superevents and {event_list.count()} MDC events that use {total_human} of space (older than {days_old} days)")

        if do_delete:
            # Delete superevents
            for s in superevent_list:
                self.stdout.write(f"\tDeleting superevent {s.superevent_id}")
                s.delete(purge=True)
            # Delete events
            for e in event_list:
                self.stdout.write(f"\tDeleting event {e.graceid}")
                e.delete(purge=True)
            self.stdout.write(self.style.SUCCESS("Done."))
        else:
            self.stdout.write(self.style.WARNING("Skipping deletion step (dry run). Use --delete to actually delete the events and superevents."))

