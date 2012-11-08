
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden, HttpResponseServerError
from django.core.urlresolvers import reverse

import simplejson

from gracedb.models import Event

import os

##################################################################
# Piston


##################################################################
# rest_framework
from rest_framework import generics, serializers

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event

class EventList(generics.ListCreateAPIView):
    model = Event       
    serializer_class = EventSerializer

class EventDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Event   
    serializer_class = EventSerializer

def api_root(request):
    """the api root"""
    return HttpResponse("""
<html>
    <head>
    </head>
    <body>
    O Hai.  %s<br/>%s
    </body>
</html>
""" % (
    reverse('event-list'),
    reverse('event-detail', args=[12]),
    ))
#""" % reverse('download', kwargs={"graceid":"G12", "filename":"FLED_THE_FILER"}))
#""" % reverse(download, args=["G12", "FRED_THE_FILE"]))

##################################################################
# Old.  Must support this.
def download(request, graceid, filename=""):
    # Do not filename to be None.  That messes up later os.path.join
    filename = filename or ""

    try:
        event = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        return HttpResponseNotFound("Event not found")

    # The plan to deal with that wretched general/ directory maybe
    # should be to move it INTO private.  Then externally, things
    # would look like they do now, but the code here would be MUCH
    # more sane and much shorter.

    # UGLY hack to deal with /private vs /general dirs
    general = False
    if filename.startswith("general/"):
        filename = filename[len("general/"):]
        general = True
        
    filepath = os.path.join(event.datadir(general), filename)

    if not os.path.exists(filepath):
        response = HttpResponseNotFound("File does not exist")
    elif not os.access(filepath, os.R_OK):
        response = HttpResponseNotFound("File not readable")
    elif os.path.isfile(filepath):
        # get an actual file.
        response = HttpResponse(open(filepath, "r"), content_type="application/octet-stream")
        response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
    elif not filename:
        # Get list of files w/urls.
        rv = {}
        filepath = event.datadir()
        for dirname, dirnames, filenames in os.walk(filepath):
            dirname = dirname[len(filepath):]  # cut off base event dir path
            for filename in filenames:
                # relative path from root of event data dir
                filename = os.path.join(dirname, filename)
                rv[filename] = reverse(download, args=[graceid, filename])

        # XXX UGH...  that awful general/ dir
        filepath = event.datadir(general=True)
        for dirname, dirnames, filenames in os.walk(filepath):
            # XXX HORRIBLE
            dirname = dirname[len(filepath)-len("general"):]  # cut off base event dir path
            for filename in filenames:
                # relative path from root of event data dir
                filename = os.path.join(dirname, filename)
                rv[filename] = reverse(download, args=[graceid, filename])

        response = HttpResponse(simplejson.dumps(rv), content_type="application/json")
    elif os.path.isdir(filepath):
        response = HttpResponseForbidden("%s is a directory" % filename)
    else:
        response = HttpResponseServerError("Should not happen.")

    return response
