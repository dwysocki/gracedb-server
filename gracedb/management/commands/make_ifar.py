
from django.core.management.base import BaseCommand, NoArgsCommand

from django.conf import settings
from gracedb.gracedb.models import Event
from gracedb.gracedb.query import parseQuery

import matplotlib
matplotlib.use('Agg')
import numpy
import scipy
import pylab
#pylab.rc('text', usetex = True)

class Command(NoArgsCommand):
    help = "I am the IFAR MAKER!"

    def handle_noargs(self, **options):

        query = parseQuery(settings.REPORT_CBC_IFAR_QUERY)
        print "query", settings.REPORT_CBC_IFAR_QUERY
        ts = []
        fars = []

        events = Event.objects.filter(query).distinct()
        print "COUNT", events.count()
        for e in events:
            ts.append(e.gpstime)
            fars.append(e.far)

        #ts,fars = numpy.loadtxt('fars.txt', unpack = True)

        fars = scipy.array(sorted(fars))
        Ns = scipy.arange(len(fars))

        T = float(max(ts) - min(ts))

        print "MAX/MIN/T", max(ts), min(ts), T

        fig = pylab.figure()
        ax = fig.add_axes((.1, .1, .8, .8))
        ax.loglog(fars, Ns, label="GraceDB CBC LowMass ER1 events")
        ax.loglog(Ns/T, Ns, label="Expected Background")
        ax.invert_xaxis()

        #ax.set_ylabel(r"$\#$")
        #ax.set_xlabel(r"\textrm{FAR (Hz)")
        #ax.set_title(r"\textrm{ER1 FARs from {\sc gstlal\_ll\_inspiral}}")

        ax.set_ylabel(r"#")
        ax.set_xlabel(r"FAR (Hz)")
        ax.set_title(r"ER1 FARs from gstlal_ll_inspiral")

        ax.text(1e-7, 3, r'$t \in [%i, %i)$'%(min(ts), max(ts)))

        pylab.legend(loc='upper right')

        pylab.savefig(settings.REPORT_IFAR_IMAGE)
