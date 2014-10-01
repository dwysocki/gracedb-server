
from django.core.management.base import BaseCommand

from gracedb.models import Event, EMBBEventLog
from gracedb.models import EMFacility
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "I am the email ingester!"

    def handle(self, *args, **options):
        graceid = args[0]

        try:
            event = Event.getByGraceid(graceid)
        except Exception, e:
            print str(e)

        # create a log entry
        eel = EMBBEventLog(event=event)
        eel.event = event
        try:
            eel.submitter = User.objects.get(username='roy.williams@LIGO.org')
        except Exception, e:
            print str(e)

        # Assign a facility name
        try:
            facility_name = 'CITT'
            facility = EMFacility.objects.get(shortName=facility_name)
            eel.facility = facility
        except Exception, e:
            print str(e)

        # Assign a facility-specific footprint ID (if provided)
        eel.footprintID = None

        # Assign the EM spectrum string
        eel.waveband = 'em.gamma'

        # Assign RA and Dec, plus widths
        eel.ra = 22
        eel.dec = 22
        eel.raWidth = 22
        eel.decWidth = 22

        # Assign gpstime and duration.
        eel.gpstime = 22
        eel.duration = 22

        # Assign EEL status and observation status.
        eel.eel_status = 'FO'
        eel.obs_status = 'TE'

        eel.extra_info_dict = None
        eel.comment = 'Hello'
        try:
            eel.save()
        except Exception as e:
            print str(e)


