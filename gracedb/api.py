
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden, HttpResponseServerError
from django.core.urlresolvers import reverse as django_reverse

import simplejson

from gracedb.models import Event

import os
import urllib

##################################################################
# Piston


##################################################################
# rest_framework
from rest_framework import serializers, status
from rest_framework.response import Response
#from rest_framework.renderers import JSONRenderer, JSONPRenderer, YAMLRenderer, XMLRenderer
from forms import CreateEventForm
from views import _createEventFromForm
from rest_framework import parsers # YAMLParser, MultiPartParser

#from rest_framework.permissions import IsAuthenticated
#from rest_framework.permissions import AllowAny
from rest_framework import authentication
from rest_framework.views import APIView
from rest_framework.reverse import reverse

from django.contrib.auth.models import User as DjangoUser


class LigoAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            user = DjangoUser.objects.get(username=request.ligouser.unixid)
        except DjangoUser.DoesNotExist:
            user = None
        return (user, None)


class EventSerializer(serializers.Serializer):
    group        = serializers.CharField(required=True, max_length=100)
    analysisType = serializers.CharField(required=True, max_length=100)

def eventToDict(event, columns=None, request=None):
    """Convert an Event to a dictionary so it can be serialized.  (ugh)"""
    # XXX Seems wrong.  Need to understand serializers.

    rv = {}

    rv['submitter'] = event.submitter.name
    rv['created'] = event.created
    rv['group'] = event.group.name
    rv['graceid'] = event.graceid()
    rv['analysisType'] = event.get_analysisType_display()
    rv['instruments'] = event.instruments
    rv['nevents'] = event.nevents
    rv['far'] = event.far
    rv['likelihood'] = event.likelihood
    rv['labels'] = [labelling.label.name for labelling in event.labelling_set.all()]
    rv['labels'] = [labelling.label.name for labelling in event.labelling_set.all()]
    rv['links'] = {
            "neighbors" : dict(
                [(e.gpstime, reverse("event-detail", args=[e.graceid()]))
                    for e in event.neighbors()]),
            "data" : event.weburl(),
            "log" : reverse("eventlog-list", args=[event.graceid()], request=request),
            "files" : reverse("files", args=[event.graceid()], request=request),
            "filemeta" : reverse("filemeta", args=[event.graceid()], request=request),
            "self" : reverse("event-detail", args=[event.graceid()], request=request),
            }
    return rv

class EventList(APIView):
    """Docstring for *EventList* class!"""
    #model = Event
    #serializer_class = EventSerializer
    ##renderer_classes = (JSONRenderer, JSONPRenderer, YAMLRenderer, XMLRenderer)
    ##permission_classes = (AllowAny,)
    ##authentication_classes = (authentication.SessionAuthentication,)
    authentication_classes = (LigoAuthentication,)
    parser_classes = (parsers.MultiPartParser,)

    def get(self, request):
        """I am the GET docstring for EventList"""
        query = request.QUERY_PARAMS.get("query")
        limit = request.QUERY_PARAMS.get("limit", 10)
        page = request.QUERY_PARAMS.get("page", 1)
        orderby = request.QUERY_PARAMS.get("orderby", "-created")
        if query is not None:
            return Response("Query not implemented")
        page = int(page)
        limit = int(limit)
        first = page*limit
        events = Event.objects.order_by(orderby)
        count = events.count()
        last = max(0, (count / limit) - 1)
        rv = {}
        rv['events'] = [eventToDict(e, request=request)
                for e in events[first:first+limit]]
        baseuri = reverse('event-list', request=request)
        d = { 'limit' : limit, 'page' : 0, "orderby": orderby }
        rv['first'] = baseuri + "?" + urllib.urlencode(d)
        d['page'] = last
        rv['last'] = baseuri + "?" + urllib.urlencode(d)
        rv['self'] = request.build_absolute_uri()
        if page != last:
            d['page'] = page+1
            rv['next'] = baseuri + "?" + urllib.urlencode(d)
        rv['total'] = count
        return Response(rv)

    def post(self, request, format=None):
        rv = {}
        form = CreateEventForm(request.POST, request.FILES)
        # XXX Implement this please.
        return Response("not yet")

        if form.is_valid():
            rv['valid'] = True
            rv['efile'] = dir(request.FILES['eventFile'])
            event, warnings = _createEventFromForm(request, form)
            rv['warnings'] = warnings
            rv['graceid'] = event.graceid()
        else:
            rv['valid'] = False
            rv['error'] = ""
            for key in form.errors:
                # as_text() not str() otherwise we get HTML.
                rv['error'] += "%s: %s\n" % (key, form.errors[key].as_text())
        return Response(rv, status=status.HTTP_201_CREATED)

class EventDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    parser_classes = (parsers.MultiPartParser,)
    form = CreateEventForm

    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("blah blah blah", status=status.HTTP_404_NOT_FOUND)
        return Response(eventToDict(event, request=request))

    def put(self, request, graceid):
        """ I am a doc.  Do I not get put anywhere? """
        raise NotImplementedError()

def eventLogToDict(log, n=None, request=None):
    # XXX Messy.  n should not be here but in the model.
    if n is None and request:
        uri = request.build_absolute_uri()
    elif n is not None and request:
        uri = reverse("eventlog-detail", args=[log.event.graceid(), n], request=request)
    else:
        uri = ""
    return [{
                "comment" : log.comment,
                "created" : log.created,
                "issuer"  : log.issuer.name,
                "self"    : uri,
            }]

class EventLogList(APIView):
    authentication_classes = (LigoAuthentication,)

    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("blah blah blah", status=status.HTTP_404_NOT_FOUND)
        logset = event.eventlog_set
        count = logset.count()
        rv = [ eventLogToDict(log, n, request)
                for (n, log) in zip(range(0,count+2), logset.iterator()) ]
        return Response(rv)

class EventLogDetail(APIView):
    """docstring for EventLogDetail"""

    authentication_classes = (LigoAuthentication,)

    def get(self, request, graceid, n):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("blah blah blah", status=status.HTTP_404_NOT_FOUND)
        rv = event.eventlog_set.all()[int(n)]
        return Response(eventLogToDict(rv, request=request))

class GracedbRoot(APIView):
    """Root of the Gracedb REST API"""
    authentication_classes = (LigoAuthentication,)
    parser_classes = ()
    def get(self, request):
        # XXX scummy way to get a URI template.  Is there better?
        detail = reverse("event-detail", args=["G1200"], request=request)
        detail = detail.replace("G1200", "{graceid}")
        log = reverse("eventlog-list", args=["G1200"], request=request)
        log = log.replace("G1200", "{graceid}")

        files = reverse("files", args=["G1200", "filename"], request=request)
        files = files.replace("G1200", "{graceid}")
        files = files.replace("filename", "{filename}")

        filemeta = reverse('filemeta', args=["G1200", "filename"], request=request)
        filemeta = filemeta.replace("G1200", "{graceid}")
        filemeta = filemeta.replace("filename", "{filename}")

        return Response({
                "event-list" : reverse("event-list", request=request),
                "event-detail-template" : detail,
                "event-log-template" : log,
                "files-template" : files,
                "filemeta-template" : filemeta,
               })

def papi_root(request):
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
    django_reverse('event-list'),
    django_reverse('event-detail', args=["G12"]),
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
                rv[filename] = django_reverse(download, args=[graceid, filename])

        # XXX UGH...  that awful general/ dir
        filepath = event.datadir(general=True)
        for dirname, dirnames, filenames in os.walk(filepath):
            # XXX HORRIBLE
            dirname = dirname[len(filepath)-len("general"):]  # cut off base event dir path
            for filename in filenames:
                # relative path from root of event data dir
                filename = os.path.join(dirname, filename)
                rv[filename] = django_reverse(download, args=[graceid, filename])

        response = HttpResponse(simplejson.dumps(rv), content_type="application/json")
    elif os.path.isdir(filepath):
        response = HttpResponseForbidden("%s is a directory" % filename)
    else:
        response = HttpResponseServerError("Should not happen.")

    return response


class Files(APIView):
    """Files Resource"""

    authentication_classes = (LigoAuthentication,)
    def get(self, request, graceid, filename=""):
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
                    rv[filename] = reverse("files", args=[graceid, filename], request=request)

            # XXX UGH...  that awful general/ dir
            # Actually not terrible, but do not like private/general as siblings.
            # Their parent is basically empty.
            filepath = event.datadir(general=True)
            for dirname, dirnames, filenames in os.walk(filepath):
                # XXX HORRIBLE
                dirname = dirname[len(filepath)-len("general"):]  # cut off base event dir path
                for filename in filenames:
                    # relative path from root of event data dir
                    filename = os.path.join(dirname, filename)
                    rv[filename] = reverse("files", args=[graceid, filename], request=request)

            #response = HttpResponse(simplejson.dumps(rv), content_type="application/json")
            response = Response(rv)
        elif os.path.isdir(filepath):
            response = HttpResponseForbidden("%s is a directory" % filename)
        else:
            response = HttpResponseServerError("Should not happen.")

        return response




class FileMeta(APIView):
    """File Metadata Resource"""
    authentication_classes = (LigoAuthentication,)
    pass
