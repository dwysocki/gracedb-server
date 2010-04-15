
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings



def histo(request):
    table = open(settings.LATENCY_REPORT_WEB_PAGE_FILE_PATH, "r").read()
    return render_to_response(
            'gracedb/histogram.html',
            {'table': table},
            context_instance=RequestContext(request))

