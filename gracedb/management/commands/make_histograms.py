
from django.conf import settings
from django.core.management.base import BaseCommand, NoArgsCommand
from django.db import connection
from django.utils import dateformat

import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot
import numpy

from gracedb.gracedb.models import Event

import os
from datetime import datetime, timedelta
from subprocess import Popen, PIPE, STDOUT


DEST_DIR = settings.LATENCY_REPORT_DEST_DIR
MAX_X = settings.LATENCY_MAXIMUM_CHARTED

WEB_PAGE_FILE_PATH = settings.LATENCY_REPORT_WEB_PAGE_FILE_PATH



class Command(NoArgsCommand):
    help = "I am the HISTOGRAM MAKER!"

    def handle_noargs(self, **options):

        now = datetime.now()

        start_day = now - timedelta(1)
        start_week = now - timedelta(7)
        start_month = now - timedelta(30)

        time_ranges =  [(start_day, "day"), (start_week, "week"), (start_month, "month")]

        annotations = {}

        # Make the histograms, save as png's.
        for atype, atype_name in Event.ANALYSIS_TYPE_CHOICES:
            annotations[atype] = {}
            for start_time, time_range in time_ranges:
                note = {}
                fname = os.path.join(DEST_DIR, "%s-%s.png" % (atype, time_range))
                note['fname'] = fname
                data = Event.objects.filter(analysisType=atype,
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
                    makePlot(data, atype, maxx=MAX_X).savefig(fname)
                annotations[atype][time_range] = note

        writeIndex(annotations, WEB_PAGE_FILE_PATH)


def writeIndex(notes, fname):

    createdDate = str(datetime.now())
    maxx = MAX_X

    table = '<table border="1" bgcolor="white">'
    table += """<caption>Tables generated: %s<br/>
                      Maximum charted latency: %s seconds</caption>""" % (createdDate, maxx)
    table += "<tr><th>&nbsp;</th>"
    for time_range in ['day', 'week', 'month']:
        table += "<th>last %s</th>" % time_range
    table += "</tr>"
    for atype, atype_name in Event.ANALYSIS_TYPE_CHOICES:
        table += "<tr>"
        table += "<td>%s</td>" % atype_name
        for time_range in ['day', 'week', 'month']:
            table += '<td align="center" bgcolor="white">'
            n = notes[atype][time_range]
            extra = ""
            if n['fname'] is not None:
                table += '<img width="400" height="300" src="%s"/>' % \
                           os.path.basename(n['fname'])
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


#=================================================================
# GNUPlot stuff.  Currently unused.
#=================================================================

# Usage:
#   d = gnuplotHistogramData(atype, start_time, now)
#   h = gnuplotHistogramImage(d, labels)
#
#   open(os.path.join(DEST_DIR,"%s-%s.png" % (atype, time_range)),"w").write(h)

def analysisTypes():
    cursor = connection.cursor()
    cursor.execute("""
        SELECT DISTINCT e.analysisType
        FROM gracedb_event e, gracedb_group g
        WHERE
          (e.group_id <> g.id AND g.name = 'Test') AND
          (e.analysisType <> 'HWINJ')
        """)
    return [x[0] for x in cursor.fetchall()]


#label = "Latencies for %s Events" % Event.getTypeLabel(atype)
#   data = Event.objects.extra(select={"date":"DATE(created)"}) \
#                           .values('date','analysisType') \
#                           .annotate(count=Count('id'))

class GnuPlot(object):
    def __init__(self, prog=None):
        self.p = Popen(
                  ["/usr/bin/gnuplot"],
                  executable="/usr/bin/gnuplot",
                  stdin=PIPE,
                  stdout=PIPE,
                  stderr=open('/dev/null','w'))
        if prog:
            self.set_prog(prog)

    def set_prog(self, prog):
        self.p.stdin.write(prog)

    def write_data(self, data):
        if isinstance(data, dict):
            for key in data:
                self.p.stdin.write("%s %s\n" % (key, data[key]))
        elif isinstance(data, tuple):
            for line in data:
                for item in data:
                    self.p.stdin.write("%s " % data)
                self.p.stdin.write("\n")

    def end_data(self, data):
        self.p.stdin.write('e\n')

    def close_data(self):
        self.p.stdin.close()

    def get_image(self):
        self.close_data()
        return self.p.stdout.read() # XXX ugh.  will it always read the whole thing?


def gnuplotHistogramData(atype, start, end):
    hist_data = {}

    data = Event.objects.filter(analysisType=atype,
                                created__range=[start, end]).exclude(group__name="Test")

    for e in data:
        latency =  e.reportingLatency()
        if latency is None:
            continue
        if latency in hist_data:
            hist_data[latency] += 1
        else:
            hist_data[latency] = 1
    return hist_data


def gnuplotHistogramImage(data, labels=[], size=(400,200)):
    if not data:
        data = { 0:0 }
    if isinstance(labels, str):
        labels = [labels]
    elif not isinstance(labels, list):
        try:
            labels = list(labels)
        except TypeError:
            labels = [labels]
    label_cmds = ""
    labeloffset = 1.05
    for label in labels:
        labeloffset -= 0.1
        label_cmds += 'set label "%s" at graph .1, %f\n' % (label, labeloffset)
    minx, maxx = min(data.keys()), max(data.keys())
    width, height = size

    plotCode = """
    set terminal png size %(width)d, %(height)d
    unset xtics
    set ytics
    set x2tics ( "%(minx)ds" %(minx)d, "%(maxx)ds" %(maxx)d )
    set xtics
    set xrange [ 0 : %(maxx)s+10 ]
    set yrange [0:]
    set boxwidth 0.9
    set style data histograms
    set style histogram cluster
    set style fill solid 1.0 border lt -1
    %(label_cmds)s
    plot "-" notitle with boxes fill
    """ % {
        "minx" : minx,
        "maxx" : maxx,
        "label_cmds" : label_cmds,
        "width" : width,
        "height" : height,
    }   
    g = GnuPlot(plotCode)
    g.write_data(data)
    return g.get_image()
