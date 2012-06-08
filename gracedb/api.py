
from django.http import HttpResponse, HttpResponseNotFound

from gracedb.models import Event

import os

def download(request, graceid, filename=None):
    #response = HttpResponse(buildVOEvent(event), content_type="application/xml")
    if not filename:
        response = HttpResponseNotFound("Not Implemented.")
        response.status_code = 404
    try:
        event = Event.getByGraceid(graceid)
        filepath = os.path.join(event.datadir(), filename)
        if not os.path.exists(filepath):
            response = HttpResponseNotFound("File does not exist")
        elif not os.access(filepath, os.R_OK):
            response = HttpResponseNotFound("File not readable")
        else:
            response = HttpResponse(open(filepath, "r"), content_type="application/octet-stream")
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
    except Event.DoesNotExist:
        response = HttpResponseNotFound("Event does not exist")

    return response
