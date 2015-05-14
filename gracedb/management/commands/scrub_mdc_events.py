import os, shutil
from django.core.management.base import NoArgsCommand
from gracedb.models import Event, Search, Group

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

            # Now, say goodbye to the database entry
            # Does this delete annotations too? That's something to test.
            e.delete()

