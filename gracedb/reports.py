
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings

import os

def histo(request):
    try:
        table = open(settings.LATENCY_REPORT_WEB_PAGE_FILE_PATH, "r").read()
    except IOError:
        table = "No Data Available"
    if os.access(settings.REPORT_IFAR_IMAGE, os.R_OK):
        ifar = settings.REPORT_IFAR_URL
    else:
        ifar = None
    return render_to_response(
            'gracedb/histogram.html',
            {'table': table,
             'ifar' : ifar,
            },
            context_instance=RequestContext(request))

