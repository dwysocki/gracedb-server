
from django.conf import settings
from django.core.management.base import BaseCommand, NoArgsCommand
from django.db import connection
from django.utils import dateformat


from gracedb.gracedb.models import Event

import os
from datetime import datetime, timedelta
from subprocess import Popen, PIPE, STDOUT


DEST_DIR = "/var/www/html/histo"


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


class Command(NoArgsCommand):
    help = "I am the HISTOGRAM MAKER!"

    def handle_noargs(self, **options):

        now = datetime.now()

        start_day = now - timedelta(1)
        start_week = now - timedelta(7)
        start_month = now - timedelta(30)

#       PAST = 91
#       now -= timedelta(PAST)
#       start_day -= timedelta(PAST)
#       start_week -= timedelta(PAST)
#       start_month -= timedelta(PAST)

        time_ranges =  [(start_day, "day"), (start_week, "week"), (start_month, "month")]

        valid_types = analysisTypes()

        for atype, atype_name in Event.ANALYSIS_TYPE_CHOICES:
            if atype not in valid_types:
                continue
            for start_time, time_range in time_ranges:
                try:
                    label = "Latencies for %s Events" % atype_name
                except KeyError:
                    label = "Bad analysis type: %s" % atype
                #labels = [label, "%s previous to %s" % (time_range, str(now))]
                labels = [label, "%s previous to %s" % (time_range, dateformat.format(now, settings.DATE_FORMAT))]
                d = histogramData(atype, start_time, now)
                h = histogramImage(d, labels)

                open(os.path.join(DEST_DIR,"%s-%s.png" % (atype, time_range)),"w").write(h)

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


def histogramData(atype, start, end):
    hist_data = {}

    data = Event.objects.filter(analysisType=atype,
                                created__range=[start, end])

    for e in data:
        latency =  e.reportingLatency()
        if latency is None:
            continue
        if latency in hist_data:
            hist_data[latency] += 1
        else:
            hist_data[latency] = 1
    return hist_data


def histogramImage(data, labels=[], size=(400,200)):
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

