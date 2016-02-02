
from django.conf import settings
from django.core.management.base import NoArgsCommand

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot
import numpy

from gracedb.models import Event, Pipeline

import os
from datetime import timedelta
from django.utils import timezone

DEST_DIR = settings.LATENCY_REPORT_DEST_DIR
MAX_X = settings.LATENCY_MAXIMUM_CHARTED

WEB_PAGE_FILE_PATH = settings.LATENCY_REPORT_WEB_PAGE_FILE_PATH
URL_PREFIX = settings.REPORT_INFO_URL_PREFIX

# XXX Branson introduced during ER6 to clean things up a bit.
PIPELINE_EXCLUDE_LIST = ['HardwareInjection', 'X', 'Q', 'Omega', 'Ringdown', 'LIB', 'SNEWS', 'pycbc', 'CWB2G']

class Command(NoArgsCommand):
    help = "I am the HISTOGRAM MAKER!"

    def handle_noargs(self, **options):

        now = timezone.now()

        start_day = now - timedelta(1)
        start_week = now - timedelta(7)
        start_month = now - timedelta(30)

        time_ranges =  [(start_day, "day"), (start_week, "week"), (start_month, "month")]

        annotations = {}

        # Make the histograms, save as png's.
        for pipeline in Pipeline.objects.all():
            if pipeline.name in PIPELINE_EXCLUDE_LIST:
                continue
            pname = pipeline.name
            annotations[pname] = {}
            for start_time, time_range in time_ranges:
                note = {}
                fname = os.path.join(DEST_DIR, "%s-%s.png" % (pname, time_range))
                note['fname'] = fname
                data = Event.objects.filter(pipeline=pipeline,
                                            created__range=[start_time, now],
                                            gpstime__gt=0) \
                                    .exclude(group__name="Test")
                note['count'] = data.count()
                data = [e.reportingLatency() for e in data]
                data = [d for d in data if d <= MAX_X and d > 0]
                note['npoints'] = len(data)
                note['over'] = note['count'] - note['npoints']
                if note['npoints'] <= 0:
                    try:
                        note['fname'] = None
                        os.unlink(fname)
                    except OSError:
                        pass
                else:
                    makePlot(data, pname, maxx=MAX_X).savefig(fname)
                annotations[pname][time_range] = note

        writeIndex(annotations, WEB_PAGE_FILE_PATH)


def writeIndex(notes, fname):

    createdDate = str(timezone.now())
    maxx = MAX_X

    table = '<table border="1" bgcolor="white">'
    table += """<caption>Tables generated: %s<br/>
                      Maximum charted latency: %s seconds</caption>""" % (createdDate, maxx)
    table += "<tr><th>&nbsp;</th>"
    for time_range in ['day', 'week', 'month']:
        table += "<th>last %s</th>" % time_range
    table += "</tr>"
    for pipeline in Pipeline.objects.all():
    #for atype, atype_name in Event.ANALYSIS_TYPE_CHOICES:
        if pipeline.name in PIPELINE_EXCLUDE_LIST:
            continue
        pname = pipeline.name
        table += "<tr>"
        table += "<td>%s</td>" % pname
        for time_range in ['day', 'week', 'month']:
            table += '<td align="center" bgcolor="white">'
            n = notes[pname][time_range]
            extra = ""
            if n['fname'] is not None:
                table += '<img width="400" height="300" src="%s"/>' % \
                           (URL_PREFIX + os.path.basename(n['fname']))
                extra = "%d total events" % n['count']
            else:
                extra = "No Applicable Events"
            if n['over'] != 0:
                extra += "<br/>%d events over maximum latency of %s seconds" % (n['over'], MAX_X)
            table += "<br/>%s" % extra
            table += "</td>"
        table += "</tr>"
    table += "</table>"

    f = open(fname, "w")
    f.write(table)
    f.close()

def makePlot(data, title, maxx=1800, facecolor='green'):
    # make sure plot is clear!
    pyplot.close()
    #nbins = maxx / 30
    nbins = numpy.logspace(1.3, numpy.log10(maxx), 50)

    pyplot.xlim([20,maxx])
    fig = pyplot.figure()

    ax = fig.add_axes((.1, .1, .8, .8))

    n, bins, patches = ax.hist(data, nbins, facecolor=facecolor)

    vmax = max(n)
    if vmax <= 10:
        vmax = 10
    elif (vmax%10) == 0:
        vmax += 10
    else:
        vmax += 10 - (vmax % 10)

    ax.set_xlabel('Seconds', fontsize=20)
    ax.set_ylabel('Number of Events', fontsize=20)
    ax.set_xscale('log')
    ax.axis([20, maxx, 0, vmax])
    ax.grid(True)

    return pyplot

