# This tool removes the GroupObjectPermission objects for MDC superevent
# log objects and superevents. The reference issue is here:
#
# https://git.ligo.org/computing/gracedb/server/-/issues/302
#
# Note that the actual data is remaining in place, just the public
# visibility permission is being removed. 

from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from superevents.models import Superevent, Log, LogGroupObjectPermission, \
                               SupereventGroupObjectPermission

if getattr(settings, 'ENABLE_AWS_XRAY', None):
    try:
        from aws_xray_sdk.core import xray_recorder
        xray_recorder.begin_segment("remove-public-perms-segment")
    except ModuleNotFoundError:
        print("aws_xray_sdk not found, skipping.")


class Command(BaseCommand):
    help="Remove public view permission for old mdc superevents log messages"

    def handle(self, *args, **options):

        # Were're worried about events greater than two weeks old. 
        days_old = 14
    
        t_now = now()
        date_cutoff = t_now - timedelta(days=days_old)

        # There is needs to be a groupobjectpermission object a log object
        # to be exposed to the public. Internal users don't require that
        # permission. So find all Log objects whose parent superevent is MDC,
        # older than our date cutoff, and whose groupobjectpermission_set isn't
        # null.

        public_mdc_log_objects = Log.objects.filter(superevent__category='M',
                                             created__lt=date_cutoff,
                                             loggroupobjectpermission__isnull=False)

        # Spit out the number of log objects that meet that criteria, just for 
        # ha ha's. 

        num_logs = public_mdc_log_objects.count()

        print(f"There are {num_logs} publicly-tagged MDC log objects")

        # Also get the list of > 14-day-old, MDC, exposed superevents in order to
        # clear their permissions too.
        public_mdc_superevents = Superevent.objects.filter(category='M',
                                     supereventgroupobjectpermission__isnull=False,
                                     created__lt=date_cutoff).distinct()

        print("Clearing log permissions.")
        for l in public_mdc_log_objects:
            l.loggroupobjectpermission_set.all().delete()

        print("--> Done clearing log permissions.")

        # Now change the visibility for the superevents:
        num_superevents = public_mdc_superevents.count()
        print(f'Clearing visiblity for {num_superevents} superevents')
        for s in public_mdc_superevents:
            s.is_exposed = False
            s.supereventgroupobjectpermission_set.all().delete()
            s.save()

        print('--> Done clearing superevent permissions')
