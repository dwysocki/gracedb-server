
from django.core.management.base import BaseCommand, NoArgsCommand

from django.conf import settings
from gracedb.gracedb.models import Event
from gracedb.gracedb.query import parseQuery

import os

import matplotlib
matplotlib.use('Agg')
import numpy
import scipy
import pylab
#pylab.rc('text', usetex = True)

def ifar_none(title, message, filename):
    fig = pylab.figure()
    ax = fig.add_axes((.1, .1, .8, .8))
    ax.set_title(title)
    ax.axis([0,10,0,10])
    ax.text(3,5,message)
    #pylab.legend(loc="center")
    pylab.savefig(filename)

def ifar_chart(events, title, axis_label, filename):

    ts = []
    fars = []

    for e in events:
        ts.append(e.gpstime)
        fars.append(e.far)

    fars = scipy.array(sorted(fars))
    Ns = scipy.arange(len(fars))

    T = float(max(ts) - min(ts))

    fig = pylab.figure()
    ax = fig.add_axes((.1, .1, .8, .8))
    ax.loglog(fars, Ns, label=axis_label)

    Ns = scipy.arange(len(fars)*10) / 10.
    ax.loglog(Ns/T, Ns, label="Expected Background")
    ax.fill_between(Ns/T, Ns - Ns**.5, Ns + Ns**.5, color='k', alpha=0.1)
    ax.fill_between(Ns/T, Ns - 2 * Ns**.5, Ns + 2 * Ns**.5, color='k', alpha=0.1)
    ax.invert_xaxis()

    ax.set_ylabel(r"#")
    ax.set_xlabel(r"FAR (Hz)")
    #ax.set_title(r"ER1 FARs from gstlal_ll_inspiral t in [%i, %i)" %(min(ts), max(ts)))
    ax.set_title(title)

    pylab.legend(loc='upper right')
    pylab.ylim([1, Ns[-1] + 2 * Ns[-1]**.5])
    pylab.xlim([fars[-1], fars[0]])

    ax.text(1e-7, 3, r'$t \in [%i, %i)$'%(min(ts), max(ts)))
    pylab.savefig(filename)
    return


    fars = scipy.array(sorted(fars))
    Ns = scipy.arange(len(fars))

    T = float(max(ts) - min(ts))

    fig = pylab.figure()
    ax = fig.add_axes((.1, .1, .8, .8))
    ax.loglog(fars, Ns, label=axis_label)
    Ns = scipy.arange(len(fars)*10) / 10
    ax.loglog(Ns/T, Ns, label="Expected Background")
    ax.fill_between(Ns/T, Ns - Ns**.5, Ns + Ns**.5, color='k', alpha=0.1)
    ax.fill_between(Ns/T, Ns - 2 * Ns**.5, Ns + 2 * Ns**.5, color='k', alpha=0.1)
    ax.invert_xaxis()

    #ax.set_ylabel(r"$\#$")
    #ax.set_xlabel(r"\textrm{FAR (Hz)")
    #ax.set_title(r"\textrm{ER1 FARs from {\sc gstlal\_ll\_inspiral}}")

    ax.set_ylabel(r"#")
    ax.set_xlabel(r"FAR (Hz)")
    ax.set_title(title)

    ax.text(1e-7, 3, r'$t \in [%i, %i)$'%(min(ts), max(ts)))

    pylab.legend(loc='upper right')
    pylab.ylim([1, Ns[-1] + 2 * Ns[-1]**.5])
    pylab.xlim([fars[-1], fars[0]])

    pylab.savefig(filename)

class Command(NoArgsCommand):
    help = "I am the IFAR MAKER!"

    def handle_noargs(self, **options):
        for (q, label, title, fname) in settings.REPORTS_IFAR:
            query = parseQuery(q)
            events = Event.objects.filter(query).distinct()
            filename = os.path.join(settings.REPORT_IFAR_IMAGE_DIR, fname)
            if events.count() > 0:
                ifar_chart(events, title, label, filename)
            else:
                ifar_none(title, "No Data", filename)
        return

        query = parseQuery("LowMass now yesterday .. now")
        events = Event.objects.filter(query).distinct()
        if events.count() > 0:
            axis_label = "GraceDB CBC LowMass ER1 events"
            title = r"ER1 FARs from gstlal_ll_inspiral - last day"
            filename = os.path.join(settings.REPORT_IFAR_IMAGE_DIR, "ifar_day.png")
            ifar_chart(events, title, axis_label, filename)
        else:
            print "No day"
            try:
                os.unlink(filename)
            except:
                pass

        query = parseQuery("LowMass a week ago .. now")
        events = Event.objects.filter(query).distinct()
        if events.count() > 0:
            axis_label = "GraceDB CBC LowMass ER1 events"
            title = r"ER1 FARs from gstlal_ll_inspiral - last week"
            filename = os.path.join(settings.REPORT_IFAR_IMAGE_DIR, "ifar_week.png")
            ifar_chart(events, title, axis_label, filename)
        else:
            print "No week"
            try:
                os.unlink(filename)
            except:
                pass

