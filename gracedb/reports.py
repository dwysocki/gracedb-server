
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings

from gracedb.models import Event
from django.db.models import Q

import os, json

from django.core.urlresolvers import reverse

from models import CoincInspiralEvent ,SingleInspiral
from forms import SimpleSearchFormWithSubclasses
from query import parseQuery


from django.db.models import Max, Min
import matplotlib
matplotlib.use('Agg')
import numpy
import matplotlib.pyplot as plot
import StringIO
import base64
import sys
import time
from datetime import datetime, timedelta
from utils import posixToGpsTime

def histo(request):

    # Latency table.
    try:
        table = open(settings.LATENCY_REPORT_WEB_PAGE_FILE_PATH, "r").read()
    except IOError:
        table = None

    # IFAR tables.

    files = [ f for (_,_,_,f) in settings.REPORTS_IFAR ]

    ifar = []
    for name in files:
        fname = os.path.join(settings.REPORT_IFAR_IMAGE_DIR, name)
        if os.access(fname, os.R_OK):
            ifar.append(name)

    # Uptime table.
    try:
        uptime = open(settings.UPTIME_REPORT_DIR + "/ytd.html", "r").read()
    except IOError:
        uptime = None


    return render_to_response(
            'gracedb/histogram.html',
            {'table': table,
             'ifar' : ifar,
             'uptime' : uptime,
             'rate' : json.dumps(rate_data(request)),
            },
            context_instance=RequestContext(request))

def rate_data(request):
    # XXX there is a better way -- should be using group_by or something.
    # WAAY too many queries (~300) going on here.
    now = datetime.now()
    day = timedelta(1)

    ts_min = now - 60 * day
    ts_max = now
    ts_step = day
    window_size = day

    types = [
        ("total",   Q()),
        ]
#   types = [
#       ("LM",      Q(analysisType="LM")),
#       ("Omega",   Q(analysisType="Omega")),
#       ("CWB",     Q(analysisType="CWB")),
#       ("MBTA",    Q(analysisType="MBTA")),
#       ("total",   Q()),
#       ]

    ts = ts_min
    n = 1
    series = dict([(name, []) for (name,_) in types])
    while ts <= ts_max:
        for atype, q in types:
            series[atype].append( 
                {
                 "x": ts.strftime("%s"),
                 "y": Event.objects.filter(q).filter(created__range=(ts, ts+day)).exclude(group__name="Test").count(),
                })
        ts += ts_step
        n += 1

    # [ (ts, event_count( ts - window_size, ts) / window_size)
    #   for ts in range(ts_min, ts_max, ts_step) ]

    return series



# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

# The following two util routines are for gstlalcbc_report. This is messy.
def cluster(events):
    # FIXME N^2 clustering, but event list should always be small anyway...
    def quieter(e1, events = events, win = 5):
        for e2 in events:
            if e2.far == e1.far:
                # XXX I need subclass attributes here.
                if (e2.gpstime < e1.gpstime + win) and (e2.gpstime > e1.gpstime - win) and (e2.snr > e1.snr):
                    return True
            else:
                if (e2.gpstime < e1.gpstime + win) and (e2.gpstime > e1.gpstime - win) and (e2.far < e1.far):
                    return True
        return False
    return [e for e in events if not quieter(e)]

def to_png_image(out = sys.stdout):
    f = StringIO.StringIO()
    plot.savefig(f, format="png")
    return base64.b64encode(f.getvalue())

def gstlalcbc_report(request, format=""):
    if not request.user or not request.user.is_authenticated():
        return HttpResponseForbidden("Forbidden")

    if request.method == "GET":
        if "query" not in request.GET:
            # Use default query. LowMass events from the past week.
            t_high = datetime.now()
            dt = timedelta(days=7)
            t_low = t_high - dt
            t_high = posixToGpsTime(time.mktime(t_high.timetuple()))
            t_low = posixToGpsTime(time.mktime(t_low.timetuple()))
            query = 'CBC LowMass %d .. %d' % (t_low, t_high)
            rawquery = query
            form = SimpleSearchFormWithSubclasses({'query': query})
        else:
            form = SimpleSearchFormWithSubclasses(request.GET)
            rawquery = request.GET['query']
    else:
        form = SimpleSearchFormWithSubclasses(request.POST)
        rawquery = request.POST['query']
    if form.is_valid():
        objects = form.cleaned_data['query']

        # Check for foreign objects.
        for obj in objects:
            if not isinstance(obj, CoincInspiralEvent):
                errormsg = 'Your query returned items that are not CoincInspiral Events. '
                errormsg += 'Please try again.'
                form = SimpleSearchFormWithSubclasses()
                return render_to_response('gracedb/gstlalcbc_report.html', 
                        { 'form':form, 'message':errormsg}, 
                        context_instance=RequestContext(request))

        # Check that we have a well-defined GPS time range.
        # Find the gpstime limits of the query by diving into the query object.
        # XXX Down the rabbit hole!
        qthing = parseQuery(rawquery)
        gpsrange = None
        for child in qthing.children:
            if 'gpstime' in str(child):
                for subchild in child.children:
                    if isinstance(subchild, tuple):
                        gpsrange = subchild[1]
        if not gpsrange:
            # Bounce back to the user with an error message
            errormsg = 'Your query does not have a gpstime range. Please try again.'
            form = SimpleSearchFormWithSubclasses()
            return render_to_response('gracedb/gstlalcbc_report.html', 
                    { 'form':form, 'message':errormsg}, 
                    context_instance=RequestContext(request))
        lt = int(gpsrange[1]) - int(gpsrange[0])

        # Check that there aren't too many objects.
        # XXX Hardcoded limit
        if objects.count() > 2000:
            errormsg = 'Your query returned too many events. Please try again.'
            return render_to_response('gracedb/gstlalcbc_report.html', 
                    { 'form':form, 'message':errormsg}, 
                    context_instance=RequestContext(request))

        # Zero events will break the min/max thing that comes next.
        if objects.count() < 1:
            errormsg = 'Your query returned no events. Please try again.'
            return render_to_response('gracedb/gstlalcbc_report.html', 
                    { 'form':form, 'message':errormsg}, 
                    context_instance=RequestContext(request))

        # Find the min and max on the set of objects.
        #gpstime_limits = objects.aggregate(Max('gpstime'), Min('gpstime'))
        mchirp_limits = objects.aggregate(Max('coincinspiralevent__mchirp'), 
                Min('coincinspiralevent__mchirp'))
        mass_limits = objects.aggregate(Max('coincinspiralevent__mass'), 
                Min('coincinspiralevent__mass'))

        clustered_events = cluster(objects)
        clustered_events = sorted(clustered_events, None, key=lambda x: x.far)

        # Make IFAR plot.
        ifars = numpy.array(sorted([1.0 / e.far for e in clustered_events])[::-1])
        N = numpy.linspace(1, len(ifars), len(ifars))

        eN = numpy.linspace(1, 1000 * len(ifars), 1000 * len(ifars)) / 1000.
        expected_ifars = lt / eN

        up = eN + eN**.5
        down = eN - eN**.5
        down[down < 0.9] = 0.9

        plot.figure(figsize=(6,5))
        plot.loglog(ifars[::-1], N[::-1])
        plot.fill_between(expected_ifars[::-1], down[::-1], up[::-1], alpha=0.1)
        plot.loglog(expected_ifars[::-1], eN[::-1])
        plot.ylim([0.9, len(ifars)])
        plot.xlabel('IFAR (s)')
        plot.ylabel('N')
        plot.grid()
        ifar_plot = to_png_image()

        # Set the color map for loudest event table. Depends on lt.
        #FAR_color_map = [ { 'max_far' : 1.e-12, 'color' : 'gold',    'desc' : '< 1/10000 yrs'},
        #        { 'max_far' : 3.e-10, 'color' : 'silver',  'desc' : '< 1/100 yrs'},
        #        { 'max_far' : 3.e-8,  'color' : '#A67D3D', 'desc' : '< 1/yr'},
        #        { 'max_far' : 1.0/lt, 'color' : '#B2C248', 'desc' : 'louder than expected'}, ]
        
        # XXX Okay, this sucks. There is no switch/case structure in the django template
        # language. So I couldn't think of any way to do this without checking ranges.
        # And the range is zero to infinity. So here I go...
        FAR_color_map = [ { 'min_far' : 0.0, 'max_far' : 1.e-12, 'color' : 'gold',    'desc' : '< 1/10000 yrs'},
                { 'min_far' : 1.e-12, 'max_far' : 3.e-10, 'color' : 'silver',  'desc' : '< 1/100 yrs'},
                { 'min_far' : 3.e-10, 'max_far' : 3.e-8,  'color' : '#A67D3D', 'desc' : '< 1/yr'},
                { 'min_far' : 3.e-8,  'max_far' : 1.0/lt, 'color' : '#B2C248', 'desc' : 'louder than expected'}, 
                { 'min_far' : 1.0/lt, 'max_far' : float('inf'), 'color' : 'white', 'desc' : ''}, ]

        # Make mass distribution plots
        mchirp = numpy.array([e.mchirp for e in clustered_events])
        plot.figure(figsize=(6,4))
        lower = int(mchirp_limits['coincinspiralevent__mchirp__min'])
        upper = int(mchirp_limits['coincinspiralevent__mchirp__max']) + 1
        # How to decide the number of bins?
        N_bins = 20
        delta = max(float(upper-lower)/N_bins,0.2)
        plot.hist(mchirp, bins=numpy.arange(lower,upper,delta))
        plot.xlabel('Chirp Mass')
        plot.ylabel('count')
        plot.grid()
        mchirp_dist = to_png_image()

        mass = numpy.array([e.mass for e in clustered_events])
        plot.figure(figsize=(6,4))
        lower = int(mass_limits['coincinspiralevent__mass__min'])
        upper = int(mass_limits['coincinspiralevent__mass__max']) + 1
        N_bins = 20
        delta = max(float(upper-lower)/N_bins,0.2)
        plot.hist(mass, bins=numpy.arange(lower,upper,delta))
        plot.xlabel('Total Mass')
        plot.ylabel('count')
        plot.grid()
        mass_dist = to_png_image()

        if objects.count() == 1:
            title = "Query returned %s event." % objects.count()
        else:
            title = "Query returned %s events." % objects.count()

        context = {
            'title': title,
            'form': form,
            'formAction': reverse(gstlalcbc_report),
            'count' : objects.count(),
            'rawquery' : rawquery,
            'FAR_color_map' : FAR_color_map,
            'mass_dist' : mass_dist,
            'mchirp_dist' : mchirp_dist,
            'ifar_plot' : ifar_plot,
            'clustered_events' : clustered_events,
        }
        return render_to_response('gracedb/gstlalcbc_report.html', context,
                context_instance=RequestContext(request))

    return render_to_response('gracedb/gstlalcbc_report.html',
            { 'form' : form,
            },
            context_instance=RequestContext(request))


