import os, shutil
from django.core.management.base import NoArgsCommand
from gracedb.models import Event, Search, Group
from gracedb.models import CoincInspiralEvent, MultiBurstEvent
from guardian.models import GroupObjectPermission
from django.contrib.contenttypes.models import ContentType

class Command(NoArgsCommand):
    help = "I kill the MDC events."

    def handle_noargs(self, **options):
        """
        Note! This needs to be run as root. The reason is that these
        directories are owned by www-data. And the 'gracedb' user 
        doesn't have sudo.
        """
        MDC = Search.objects.get(name='MDC')
        Test = Group.objects.get(name='Test')
        events = Event.objects.filter(search=MDC).exclude(group=Test)

        for e in events:
            datadir = e.datadir()
            graceid = e.graceid()
            print "Deleting %s, %s" % (graceid, datadir)
            # First we need to clean up the data directory
            # Note. rmtree with throw OSError if the datadir is a softlink.
            # Even though there are softlinks farther up the chain, the leafdir
            # in question here can be removed by rmtree.
            if os.path.isdir(datadir):
                shutil.rmtree(datadir)

            # Uhm. For debugging purposes, did we get it?
            if os.path.isdir(datadir):
                print 'Problem! Have not deleted datadir %s' % datadir
                exit(1)

            # We need to delete the relevant GroupObjectPermission objects as well.
            # Any CoincInspiralEvent for this event? If so, delete their associated 
            # GroupObjectPermissions.
            try:
                coinc_event = CoincInspiralEvent.objects.get(id=e.id)
                ctype = ContentType.objects.get(app_label='gracedb', model='coincinspiralevent')
                gops = GroupObjectPermission.objects.filter(object_pk=e.id, content_type=ctype)
                for g in gops:
                    g.delete() 
            except:
                pass

            # Any MultiBurstEvent for this event? If so, delete their associated 
            # GroupObjectPermissions.
            try:
                coinc_event = MultiBurstEvent.objects.get(id=e.id)
                ctype = ContentType.objects.get(app_label='gracedb', model='multiburstevent')
                gops = GroupObjectPermission.objects.filter(object_pk=e.id, content_type=ctype)
                for g in gops:
                    g.delete() 
            except:
                pass

            # Finally delete the GroupObjectPermissions on the Event itself.
            ctype = ContentType.objects.get(app_label='gracedb', model='event')
            gops = GroupObjectPermission.objects.filter(object_pk=e.id, content_type=ctype)
            for g in gops:
                g.delete() 

            # Now, say goodbye to the database entry
            e.delete()

