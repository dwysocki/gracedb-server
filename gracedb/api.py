
from django.http import HttpResponse, HttpResponseNotFound
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.core.urlresolvers import reverse as django_reverse

from django.conf import settings

import json

from gracedb.models import Event, Group, EventLog, Tag
from gracedb.views import create_label
from translator import handle_uploaded_data

from alert import issueAlertForUpdate

import os
import urllib
import errno
import shutil

from utils.vfile import VersionedFile

##################################################################

REST_FRAMEWORK_SETTINGS = getattr(settings, 'REST_FRAMEWORK', {})
PAGINATE_BY = REST_FRAMEWORK_SETTINGS.get('PAGINATE_BY', 10)

##################################################################
# rest_framework
from rest_framework import serializers, status
from rest_framework.response import Response
#from rest_framework.parsers import BaseParser
#from rest_framework import generics
#from rest_framework.renderers import JSONRenderer, JSONPRenderer
#from rest_framework.renderers import YAMLRenderer, XMLRenderer
from forms import CreateEventForm
from views import _createEventFromForm
from rest_framework import parsers      # YAMLParser, MultiPartParser
from rest_framework.parsers import DataAndFiles

from rest_framework.permissions import IsAuthenticated
#from rest_framework.permissions import AllowAny
from rest_framework import authentication
from rest_framework.views import APIView

from django.contrib.auth.models import User as DjangoUser

MAX_FAILED_OPEN_ATTEMPTS = 5

from forms import SimpleSearchForm


from rest_framework.reverse import reverse as rest_framework_reverse
from django.core.urlresolvers import resolve, get_script_prefix

# Note about reverse() in this file -- there are THREE versions of it here.
#
# SOURCE                               LOCAL NAME
# django.core.urlresolvers.reverse ==> django_reverse
# rest_framework.reverse.reverse   ==> rest_framework_reverse
# reverse defined below            ==> reverse
#
# The Django reverse returns relative paths.
#
# The rest framework reverse is basically the same as the Django version
# but will return full paths if the request is passed in using the request kw arg.
#
# The reverse defined below is basically the rest framework reverse, but
# will attempt to deal with multiply-include()-ed url.py-type files with
# different namespaces.  (see the comments in the function)

def reverse(name, *args, **kw):
    """Find a URL.  Respect where that URL was defined in urls.py

    Allow for a set of URLs to have been include()-ed on multiple URL paths.

    eg  urlpatterns = (
        (r'^api1/', include('someapp.urls', app_name="api", namespace="x509")),
        (r'^api2/', include('someapp.urls', app_name="api", namespace="shib")),
        ...)

    then reverse("api:root", request=self.request) will give the obviously
    correct full URL for the URL named "root" in someapp/urls.py.  Django's
    reverse will pick one URL path and use it no matter what path the
    URL resolver flows through and it will do so whether you specify an app_name
    or not.

    This function solves that issue.  app_name and namespace are required.
    The request must be the value at kw['request']

    Assembled with hints from http://stackoverflow.com/a/13249060
    """
    # XXX rashly assuming app is "api:"  brutal.
    if type(name) == str and not name.startswith("api:"):
        name = "api:"+name

    # Idea is to put 'current_app' into the kw args of reverse
    # where current_app is the namespace of the urlpattern we got here from.
    # Given that, reverse will find the right patterns in your urlpatterns.
    # I do know know why Django does not do this by default.

    # This probably only works if you give app_names which are the same
    # and namespaces that are different.

    if 'request' in kw and 'current_app' not in kw:
        request = kw['request']
        # For some reason, resolve() does not seem to like the script_prefix.
        # So, remove it.
        prefix = get_script_prefix()
        path = request.path.replace(prefix, '/')
        current_app = resolve(path).namespace
        kw['current_app'] = current_app

    return rest_framework_reverse(name, *args, **kw)

class LigoAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        # LIGOAuth middleware finds you from X509 cert, but
        # Shib middleware clobbers (?) the Django user in request
        # and identifies you as anonymous.  Need to recover the
        # Django user.
        try:
            user = DjangoUser.objects.get(username=request.ligouser.unixid)
        except DjangoUser.DoesNotExist:
            # XXX Probably need to create a user.
            user = None
        return (user, None)


class EventSerializer(serializers.ModelSerializer):
    #group        = serializers.CharField(required=True, max_length=100)
    #analysisType = serializers.CharField(required=True, max_length=100)
    group = serializers.CharField(source="group.name")
    class Meta:
        model = Event
        fields = ('far', 'instruments', 'group')

class EventLogSerializer(serializers.ModelSerializer):
    """docstring for EventLogSerializer"""
    comment =  serializers.CharField(required=True, max_length=200)
    class Meta:
        model = EventLog
        fields = ('comment', 'issuer', 'created')

#==================================================================
# Events

def eventToDict(event, columns=None, request=None):
    """Convert an Event to a dictionary so it can be serialized.  (ugh)"""

    # XXX  Need to understand serializers.

    rv = {}

    graceid = event.graceid()
    rv['submitter'] = event.submitter.name
    rv['created'] = event.created
    rv['group'] = event.group.name
    rv['graceid'] = graceid
    rv['analysisType'] = event.get_analysisType_display()
    rv['gpstime'] = event.gpstime
    rv['instruments'] = event.instruments
    rv['nevents'] = event.nevents
    rv['far'] = event.far
    rv['likelihood'] = event.likelihood
    rv['labels'] = dict([
            (labelling.label.name,
                reverse("labels",
                    args=[graceid, labelling.label.name],
                    request=request))
            for labelling in event.labelling_set.all()])
    rv['links'] = {
            "neighbors" : reverse("neighbors", args=[graceid], request=request),
            "log"   : reverse("eventlog-list", args=[graceid], request=request),
            "files" : reverse("files", args=[graceid], request=request),
            "filemeta" : reverse("filemeta", args=[graceid], request=request),
            "labels" : reverse("labels", args=[graceid], request=request),
            "self"  : reverse("event-detail", args=[graceid], request=request),
            "tags"  : reverse("eventtag-list", args=[graceid], request=request),
            }
    return rv


class EventList(APIView):
    """
    This resource represents the collection of  all candidate events in GraceDB.

    ### GET
    Retrieve events. You may use the following parameters:

    * `query=Q`    : use any query string as one might use on the query page.
    * `count=N`    : the maximum number of events in a response. (default: 10)
    * `start=N`    : events starting with the Nth event. (default: 0)
    * `sort=Order` : how to order events.  (default: -created)

    Example:
    `curl -X GET --insecure --cert $X509_USER_PROXY https://gracedb.ligo.org/api/events/?query=LowMass%20EM_READY&orderby=-far`

    Add header `Accept: application/ligolw` for ligolw formatted response.

    ### POST
    To create an event.  Expects `multipart/form-data` mime-type with
    parameters, `group`, `type` and a file part, `eventFile` containing
    the analysis data.

    Allowable groups and analysis types are listed in the root resource.

    Example:
    `curl -X POST -F "group=Test" -F "type=LM" -F "eventFile=@coinc.xml" --insecure --cert $X509_USER_PROXY https://gracedb.ligo.org/api/events/`

    """
    #model = Event
    #serializer_class = EventSerializer
    ##renderer_classes = (JSONRenderer, JSONPRenderer, YAMLRenderer, XMLRenderer)
    ##permission_classes = (AllowAny,)
    ##authentication_classes = (authentication.SessionAuthentication,)
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (parsers.MultiPartParser,)

# XXX Need a LIGOLW renderer
#   def cli_search(request):
#      assert request.ligouser
#      from views import assembleLigoLw
#      form = SimpleSearchForm(request.POST)
#      if form.is_valid():
#          query = form.cleaned_data['query']
#          objects = Event.objects.filter(query).distinct()

#          if 'ligolw' in request.POST or 'ligolw' in request.GET:
#              from glue.ligolw import utils
#              if objects.count() > 1000:
#                  return Response("Too many events.",
#                          status=status.HTTP_400_BAD_REQUEST)
#              xmldoc = assembleLigoLw(objects)
#              response = HttpResponse(mimetype='application/xml')
#              response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
#              utils.write_fileobj(xmldoc, response)
#              return response


    def get(self, request):
        """I am the GET docstring for EventList"""

        query = request.QUERY_PARAMS.get("query")
        count = request.QUERY_PARAMS.get("count", PAGINATE_BY)
        start = request.QUERY_PARAMS.get("start", 0)
        sort = request.QUERY_PARAMS.get("sort", "-created")

        events = Event.objects
        if query:
            form = SimpleSearchForm(request.GET)
            if form.is_valid():
                cooked_query = form.cleaned_data['query']
                events = events.filter(cooked_query).distinct()
            else:
                return Response("Invalid query",
                        status=status.HTTP_400_BAD_REQUEST)
        events = events.order_by(sort)

        start = int(start)
        count = int(count)
        numRows = events.count()
        last = max(0, (numRows / count)) * count
        rv = {}
        links = {}
        rv['links'] = links
        rv['events'] = [eventToDict(e, request=request)
                for e in events[start:start+count]]
        baseuri = reverse('event-list', request=request)

        links['self'] = request.build_absolute_uri()

        d = { 'start' : 0, "count": count, "sort": sort }
        if query: d['query'] = query
        links['first'] = baseuri + "?" + urllib.urlencode(d)

        d['start'] = last
        links['last'] = baseuri + "?" + urllib.urlencode(d)

        if start != last:
            d['start'] = start+count
            links['next'] = baseuri + "?" + urllib.urlencode(d)
        rv['numRows'] = events.count()
        d['links'] = links
        return Response(rv)

    def post(self, request, format=None):
        form = CreateEventForm(request.POST, request.FILES)
        if form.is_valid():
            event, warnings = _createEventFromForm(request, form)
            if event:
                response = Response(
                        eventToDict(event, request=request),
                        status=status.HTTP_201_CREATED)
                response["Location"] = reverse(
                        'event-detail',
                        args=[event.graceid()],
                        request=request)
                return response
            else: # no event created
                return Response({'warnings':warnings},
                        status=status.HTTP_400_BAD_REQUEST)
        else: # form not valid
            rv = {}
            rv['errors'] = ["%s: %s" % (key, form.errors[key].as_text())
                    for key in form.errors]
            return Response(rv, status=status.HTTP_400_BAD_REQUEST)


class RawdataParser(parsers.BaseParser):
    media_type = 'application/octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        class FakeFile():
            def __init__(self, name, read):
                self.name = name
                self.read = read
        files = { 'upload' : FakeFile("initial.data", stream.read) }
        data = {}
        return DataAndFiles(data, files)

class LigoLwParser(parsers.MultiPartParser):
    # XXX Revisit this.
    #  Doing it right involves refactoring translator.py
    media_type = "multipart/form-data"
    def parse(self, *args, **kwargs):
        data = parsers.MultiPartParser.parse(self, *args, **kwargs)
        return data

#       eventData = data.files['eventFile'].read()

#       dirPrefix = settings.GRACEDB_DATA_DIR
#       eventDir = os.path.join(dirPrefix, event.graceid())
#       # XXX handle duplicate file names.
#       f = request.FILES['eventFile']
#       uploadDestination = os.path.join(eventDir, "private", f.name)
#       fdest = open(uploadDestination, 'w')
#       # Save uploaded file into user private area.
#       for chunk in f.chunks():
#           fdest.write(chunk)
#       fdest.close()

#       # Extract Info from uploaded data
#       try:
#           handle_uploaded_data(event, uploadDestination)
#       except:
#           return Response("Bad Data",
#                   status=status.HTTP_400_BAD_REQUEST)
#       return Response(status=status.HTTP_202_ACCEPTED)


class EventDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    #parser_classes = (LigoLwParser, RawdataParser)
    parser_classes = (parsers.MultiPartParser,)
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    form = CreateEventForm

    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event Not Found",
                    status=status.HTTP_404_NOT_FOUND)

        #response = Response(self.serializer_class(event).data)
        response = Response(eventToDict(event, request=request))

        response["Cache-Control"] = "no-cache"
        return response

    def put(self, request, graceid):
        """ I am a doc.  Do I not get put anywhere? """
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            return Response("Event Not Found",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            if request.ligouser != event.submitter:
                msg = "You (%s) Them (%s)" % (request.ligouser, event.submitter)
                return HttpResponseForbidden("You did not create this event. %s" %msg)
        except Exception, e:
            return Response(str(e))

#       messages = []
#       if event.group.name != request.DATA['group']:
#           messages += [
#                   "Existing event group ({0}) does not match "
#                   "replacement event group ({1})".format(
#                       event.group.name, request.DATA['group'])]
#       if event.analysisType != request.DATA['type']:
#           messages += [
#                   "Existing event type ({0}) does not match "
#                   "replacement event type ({1})".format(
#                       event.analysisType, request.DATA['type'])]
#       if messages:
#           return Response("\n".join(messages),
#                   status=status.HTTP_400_BAD_REQUEST)

        dirPrefix = settings.GRACEDB_DATA_DIR
        eventDir = os.path.join(dirPrefix, event.graceid())
        # XXX handle duplicate file names.
        f = request.FILES['eventFile']
        uploadDestination = os.path.join(eventDir, "private", f.name)
        fdest = VersionedFile(uploadDestination, 'w')
        # Save uploaded file into user private area.
        #for chunk in f.chunks():
        #    fdest.write(chunk)
        #fdest.close()
        shutil.copyfileobj(f, fdest)
        fdest.close()

        # Extract Info from uploaded data
        try:
            handle_uploaded_data(event, uploadDestination)
            event.submitter = request.ligouser
        except:
            # XXX Bad news.  If the log file fails to save because of
            # race conditions, then this will also be the the message
            # returned.  Somehow, I think there are other things that
            # could go wrong inside handle_uploaded_data besides just
            # bad data.  We should probably check for different types
            # of exceptions here.
            return Response("Bad Data",
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

#==================================================================
# Neighbors

class EventNeighbors(APIView):
    """The neighbors of an event.
    ### GET
    The `neighborhood` parameter lets you select a GPS time
    range for what it means to be a neighbor.  Can be of the
    form `neighborhood=N` or `neighborhood=N,M` to select
    neighbors in the (inclusive) GPS time range [x-N,x+N] or [x-N, x+M],
    where x is the GPS time of the event in question.
    """
    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        if request.QUERY_PARAMS.has_key('neighborhood'):
            delta = request.QUERY_PARAMS['neighborhood']
            try:
                if delta.find(',') < 0:
                    neighborhood = (int(delta), int(delta))
                else:
                    neighborhood = map(int, delta.split(','))
            except ValueError:
                pass
        else:
            neighborhood = event.DEFAULT_EVENT_NEIGHBORHOOD

        neighbors = event.neighbors(neighborhood=neighborhood)

        neighbors = [eventToDict(neighbor, request=request)
                    for neighbor in neighbors]
        return Response({
                'neighbors' : neighbors,
                'neighborhood' : neighborhood,
                'numRows' : len(neighbors),
                'links' : {
                    'self': request.build_absolute_uri(),
                    'event': reverse("event-detail", args=[graceid], request=request),
                    }
                })

#==================================================================
# Labels

# XXX NOT FINISHED

def labelToDict(label, request=None):
    return { 
            "name" : label.label.name,
            "creator" : label.creator.name,
            "created" : label.created,
            "self" : reverse("labels",
                args=[label.event.graceid(), label.label.name],
                request=request),
           }

class EventLabel(APIView):
    """Event Label"""
    authentication_classes = (LigoAuthentication,)

    def get(self, request, graceid, label):
        event = Event.getByGraceid(graceid)
        if label is not None:
            theLabel = event.labelling_set.filter(label__name=label).all()
            if len(theLabel) < 1:
                return Response("Label Not %s Found" % label,
                        status=status.HTTP_404_NOT_FOUND)
            theLabel = theLabel[0]
            return Response(labelToDict(theLabel, request=request))
        else:
            labels = [ labelToDict(x,request=request)
                    for x in event.labelling_set.all() ]
            return Response({
                'links' : [{
                    'self': request.build_absolute_uri(),
                    'event': reverse("event-detail",
                        args=[event.graceid()],
                        request=request),
                    }],
                'labels': labels
                })

    def put(self, request, graceid, label):
        #return Response("Not Implemented", status=status.HTTP_501_NOT_IMPLEMENTED)
        try:
            rv = create_label(graceid, label, request.ligouser)
        except Event.DoesNotExist:
            msg = "No such Event '%s'" % graceid
            return Response(msg,status=status.HTTP_404_NOT_FOUND)
        except ValueError, e:
            return Response(e.message,
                        status=status.HTTP_400_BAD_REQUEST)
        return Response(rv, status=status.HTTP_201_CREATED)

    def delete(self, request, graceid, label):
        return Response("Not Implemented", status=status.HTTP_501_NOT_IMPLEMENTED)

#==================================================================
# EventLog

# Janky serialization
def eventLogToDict(log, request=None):
    taglist_uri = None
    if request:
        uri = reverse("eventlog-detail",
                args=[log.event.graceid(), log.N],
                request=request)
        taglist_uri = reverse("eventlogtag-list",
                args=[log.event.graceid(), log.N],
                request=request)
    else:
        uri = None
    return {
                "comment" : log.comment,
                "created" : log.created,
                "issuer"  : log.issuer.name,
                "self"    : uri,
                "tags"    : taglist_uri,
           }

class EventLogList(APIView):
    """Event Log List Resource

    POST param 'message'
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        logset = event.eventlog_set.order_by("created","N")
        count = logset.count()

        log = [ eventLogToDict(log, request)
                for log in logset.iterator() ]

        rv = {
                'start': 0,
                'numRows' : count,
                'links' : {
                    'self' : request.build_absolute_uri(),
                    'first' : request.build_absolute_uri(),
                    'last' : request.build_absolute_uri(),
                    },
                'log' : log,
             }
        return Response(rv)

    def post(self, request, graceid):
        event = Event.getByGraceid(graceid)
        message = request.DATA.get('message')
        tagname = request.DATA.get('tagname')
        logentry = EventLog(
                event=event,
                issuer=request.ligouser,
                comment=message)
        logset = event.eventlog_set.order_by("created","N")
        try:
            logentry.save()
        except Exception as e:
            # Since this is likely due to race conditions, we will return 503
            return Response("Failed to save log entry: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
        rv = eventLogToDict(logentry, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']

        if tagname:
            n = logentry.N
            # XXX This is not what these API views are really meant for, but...
            tmp = EventLogTagDetail()
            retval = tmp.put(request, graceid, n, tagname) 
            # XXX This seems like a bizarre way of getting an error message out.
            if retval.status_code != 201:
                response['tagWarning'] = 'Error creating tag.'

        return response

class EventLogDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid, n):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            return Response("Event Not Found",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            rv = event.eventlog_set.filter(N=n)[0]
        except:
            return Response("Log Message Not Found",
                    status=status.HTTP_404_NOT_FOUND)

        return Response(eventLogToDict(rv, request=request))

#==================================================================
# Tags


def tagToDict(tag, columns=None, request=None, event=None, n=None):
    """Convert a tag to a dictionary.
       Output depends on the level of specificity.
    """

    rv = {}
    rv['name'] = tag.name
    rv['displayName'] = tag.displayName
    if event:
        if n:
            # We want a link to the self only.  End of the line.
            rv['links'] = {
                            "self" : reverse("eventlogtag-detail",
                                             args=[event.graceid(),n,tag.name],
                                             request=request)
                          }
        else:
            # Links to all log messages of the event with this tag.
            rv['links'] = {
                            "logs" : [reverse("eventlog-detail", 
                                              args=[event.graceid(),log.N], 
                                              request=request) 
                                      for log in event.getLogsForTag(tag.name)],
                            "self" : reverse("eventtag-detail",
                                             args=[event.graceid(),tag.name],
                                             request=request)
                          }
    else:
        # XXX Unclear what the tag detail resource should be at this level.
        # For now, return an empty list.
        pass
#         rv['links'] = {
#                         "events" : [reverse("event-detail", 
#                                             args=[event.graceid()], 
#                                             request=request) 
#                                     for event in tag.getEvents()],
#                         "self"   : reverse("tag-detail",
#                                            args=[tag.name],
#                                            request=request)
#                       }
    return rv

class TagList(APIView):
    """Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # Return a list of links to all tag objects.
        rv = {
#                 'tags' : [ reverse("tag-detail", args=[tag.name],
#                                    request=request)
#                            for tag in Tag.objects.all() ]
#                For now, we just output the tag names, since we don't know what 
#                tag-detail should look like.
                 'tags' : [ tag.name for tag in Tag.objects.all() ]
             }
        return Response(rv)

# XXX Unclear what the tag detail resource should be.
# class TagDetail(APIView):
#     """Tag Detail Resource
#     """
#     authentication_classes = (LigoAuthentication,)
#     permission_classes = (IsAuthenticated,)
# 
#     def get(self, request, tagname):
#         try:
#             tag = Tag.objects.filter(name=tagname)[0]
#         except Tag.DoesNotExist:
#             return Response("Tag not found.",
#                     status=status.HTTP_404_NOT_FOUND)
#         return Response(tagToDict(tag,request=request))

class EventTagList(APIView):
    """Event Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid):
        # Return a list of links to all tags for this event.
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)

        rv = {
                'tags' : [ reverse("eventtag-detail",args=[graceid,
                                   tag.name],
                                   request=request)
                           for tag in event.getAvailableTags()]
             }

        return Response(rv)

class EventTagDetail(APIView):
    """Event Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid, tagname):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            tag = Tag.objects.filter(name=tagname)[0]
            rv = tagToDict(tag,event=event,request=request)
            return Response(rv)
        except Tag.DoesNotExist:
            return Response("No such tag for event.",
                    status=status.HTTP_404_NOT_FOUND)

class EventLogTagList(APIView):
    """Event Log Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid, n):
        # Return a list of links to tags associated with a given log message
        try:
            event = Event.getByGraceid(graceid)
            eventlog = event.eventlog_set.filter(N=n)[0]
        except Event.DoesNotExist:
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Log does not exist.",
                    status=status.HTTP_404_NOT_FOUND)

        rv = {
                'tags' : [ reverse("eventlogtag-detail",
                                    args=[graceid, 
                                    n, tag.name],
                                    request=request)
                           for tag in eventlog.tag_set.all()]
             }

        return Response(rv)

class EventLogTagDetail(APIView):
    """Event Log Tag Detail Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, graceid, n, tagname):
        try:
            event = Event.getByGraceid(graceid)
            eventlog = event.eventlog_set.filter(N=n)[0]
        except Event.DoesNotExist:
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Log does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            tag = eventlog.tag_set.filter(name=tagname)[0]
            # Serialize
            return Response(tagToDict(tag,event=event,n=n,request=request))
        except:
            return Response("Tag not found.",status=status.HTTP_404_NOT_FOUND)

    def put(self, request, graceid, n, tagname):
        try:
            event = Event.getByGraceid(graceid)
            eventlog = event.eventlog_set.filter(N=n)[0]
        except Event.DoesNotExist:
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        except:
            return Response("Log does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            # Has this tag-eventlog relationship already been created? If so, kick out.
            # Actually, adding the eventlog to the tag would not hurt anything--no
            # duplicate entry would be made in the database.  However, we don't want
            # an extra log entry, or a deceptive HTTP response (i.e., one telling the 
            # client that the creation was sucessful when, in fact, the database
            # was unchanged.
            tag = eventlog.tag_set.filter(name=tagname)[0]
            msg = "Log already has tag %s" % unicode(tag)
            return Response(msg,status=status.HTTP_409_CONFLICT)
        except:
            # Look for the tag.  If it doesn't already exist, create it.
            try:
                tag = Tag.objects.filter(name=tagname)[0]
            except:
                displayName = request.DATA.get('displayName')
                tag = Tag(name=tagname, displayName=displayName)
                tag.save()

            # Now add the log message to this tag.
            tag.eventlogs.add(eventlog)

            # Create a log entry to document the tag creation.
            msg = "Tagged message %s: %s " % (n, tagname)
            logentry = EventLog(event=event,
                               issuer=request.ligouser,
                               comment=msg)
            try:    
                logentry.save()
            except Exception as e:
                # Since the tag creation was successful, we'll return 201.
                return Response("Tag succesful, but failed to create log entry: %s" % str(e),
                     status=status.HTTP_201_CREATED)

            return Response("Tag created.",status=status.HTTP_201_CREATED)

    def delete(self, request, graceid, n, tagname):
        try:
            event = Event.getByGraceid(graceid)
            eventlog = event.eventlog_set.filter(N=n)[0]
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        except:
            # XXX Real error message.
            return Response("Log does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        try:
            tag = eventlog.tag_set.filter(name=tagname)[0]
            tag.eventlogs.remove(eventlog)

            # Is the tag empty now?  If so we can delete it.
            if not tag.eventlogs.all():
                tag.delete()

            # Create a log entry to document the tag creation.
            msg = "Removed tag %s for message %s. " % (tagname, n)
            logentry = EventLog(event=event,
                               issuer=request.ligouser,
                               comment=msg)
            try:    
                logentry.save()
            except Exception as e:
                # Since the tag creation was successful, we'll return 200.
                return Response("Tag removed, but failed to create log entry: %s" % str(e),
                     status=status.HTTP_200_OK)

            return Response("Tag deleted.",status=status.HTTP_200_OK)
        except:
            return Response("Tag not found.",status=status.HTTP_404_NOT_FOUND)


#==================================================================
# Root Resource

class GracedbRoot(APIView):
    """
        Root of the Gracedb REST API
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = ()
    def get(self, request):
        # XXX This seems like a scummy way to get a URI template.
        # Is there better?
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

        labels = reverse('labels', args=["G1200", "thelabel"], request=request)
        labels = labels.replace("G1200", "{graceid}")
        labels = labels.replace("thelabel", "{label}")

        taglist = reverse("eventlogtag-list", args=["G1200", "0"], request=request)
        taglist = taglist.replace("G1200", "{graceid}")
        taglist = taglist.replace("0", "{n}")

        tag = reverse("eventlogtag-detail", args=["G1200", "0", "tagname"], request=request)
        tag = tag.replace("G1200", "{graceid}")
        tag = tag.replace("0", "{n}")
        tag = tag.replace("tagname", "{tagname}")

        # XXX Need a template for the tag list?

        templates = {
                "event-detail-template" : detail,
                "event-log-template" : log,
                "event-label-template" : labels,
                "files-template" : files,
                "filemeta-template" : filemeta,
                "tag-template" : tag,
                "taglist-template" : taglist,
                }

        return Response({
            "links" : {
                "events" : reverse("event-list", request=request),
                },
            "templates" : templates,
            "groups" : [group.name for group in Group.objects.all()],
            "analysis-types" : dict(Event.ANALYSIS_TYPE_CHOICES),
           })

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
        content_type, encoding = VersionedFile.guess_mimetype(filepath)
        content_type = content_type or "application/octet-stream"
        # XXX encoding should probably not be ignored.
        response = HttpResponse(open(filepath, "r"), content_type=content_type)
        if content_type == "application/octet-stream":
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
        if encoding is not None:
            response['Content-Encoding'] = encoding
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

        response = HttpResponse(json.dumps(rv), content_type="application/json")
    elif os.path.isdir(filepath):
        response = HttpResponseForbidden("%s is a directory" % filename)
    else:
        response = HttpResponseServerError("Should not happen.")

    return response

class Files(APIView):
    """Files Resource"""

    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    #parser_classes = (RawdataParser,)
    parser_classes = (parsers.MultiPartParser,)

    def get(self, request, graceid, filename=""):
        # Do not filename to be None.  That messes up later os.path.join
        filename = filename or ""

        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            return HttpResponseNotFound("Event not found")

        # The plan to deal with that general/ directory maybe
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
            content_type, encoding = VersionedFile.guess_mimetype(filepath)
            content_type = content_type or "application/octet-stream"
            # XXX encoding should probably not be ignored.
            response = HttpResponse(open(filepath, "r"), content_type=content_type)
            if content_type == "application/octet-stream":
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
            if encoding is not None:
                response['Content-Encoding'] = encoding
        elif not filename:
            # Get list of files w/urls.
            rv = {}
            filepath = event.datadir()
            files = []
            for dirname, dirnames, filenames in os.walk(filepath):
                dirname = dirname[len(filepath):]  # cut off base event dir path
                for filename in filenames:
                    # relative path from root of event data dir
                    filename = os.path.join(dirname, filename)
                    rv[filename] = reverse("files", args=[graceid, filename], request=request)
                    files.append({
                            'name' : filename,
                            'link' :  reverse("files",
                                args=[graceid, filename],
                                request=request),
                            })

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
                    files.append({
                            'name' : filename,
                            'link' :  reverse("files",
                                args=[graceid, filename],
                                request=request),
                            })

            #response = HttpResponse(simplejson.dumps(rv), content_type="application/json")
#           response = Response({
#               'links' : {
#                   'self' : request.build_absolute_uri(),
#                   'event' : reverse("event-detail",
#                       args=[graceid],
#                       request=request),
#                   },
#               'files' : files,
#               })
            response = Response(rv)
        elif os.path.isdir(filepath):
            # XXX Really?
            response = HttpResponseForbidden("%s is a directory" % filename)
        else:
            response = HttpResponseServerError("Should not happen.")

        return response

    def put(self, request, graceid, filename=""):
        """ File uploader.  Implements file versioning. """
        filename = filename or ""

        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            return HttpResponseNotFound("Event not found")

        if filename.startswith("general/"):
            # No writing to general/
            return HttpResponseForbidden("cannot write to general directory")

        filepath = os.path.join(event.datadir(), filename)

        try:
            # Open / Write the file.
            fdest = VersionedFile(filepath, 'w')
            f = request.FILES['upload']
            for chunk in f.chunks(): 
                fdest.write(chunk)
            fdest.close()

            rv = {}
            # XXX this seems wobbly.
            longname = fdest.name
            shortname = longname[longname.rfind(filename):]
            rv['permalink'] = reverse(
                    "files", args=[graceid, shortname], request=request)
            response = Response(rv, status=status.HTTP_201_CREATED)
        except Exception, e:
            # XXX This needs some thought.
            response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        try:
            description = "UPLOAD: {0}".format(filename)
            issueAlertForUpdate(event, description, doxmpp=True, filename=filename)
        except:
            # XXX something should be done here.
            pass

        return response

class FileMeta(APIView):
    """File Metadata Resource"""
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    pass

