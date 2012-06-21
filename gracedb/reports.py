
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings

from gracedb.models import Event
from django.db.models import Q

import os, datetime, json, time

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
    now = datetime.datetime.now()
    day = datetime.timedelta(1)

    ts_min = now - 60 * day
    ts_max = now
    ts_step = day
    window_size = day

    types = [
        ("LM",      Q(analysisType="LM")),
        ("Omega",   Q(analysisType="Omega")),
        ("CWB",     Q(analysisType="CWB")),
        ("MBTA",    Q(analysisType="MBTA")),
        ("total",   Q()),
        ]

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


