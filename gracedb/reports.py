
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings

import os

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
            },
            context_instance=RequestContext(request))

