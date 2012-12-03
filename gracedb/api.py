
from django.http import HttpResponse, HttpResponseNotFound
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.core.urlresolvers import reverse as django_reverse

from django.conf import settings

import json

from gracedb.models import Event, Group, EventLog, Label
from translator import handle_uploaded_data

import os
import urllib
import errno
import logging

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

#from rest_framework.permissions import IsAuthenticated
#from rest_framework.permissions import AllowAny
from rest_framework import authentication
from rest_framework.views import APIView
from rest_framework.reverse import reverse

from django.contrib.auth.models import User as DjangoUser

MAX_FAILED_OPEN_ATTEMPTS = 5

from forms import SimpleSearchForm

class LigoAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            user = DjangoUser.objects.get(username=request.ligouser.unixid)
        except DjangoUser.DoesNotExist:
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
#           "neighbors" : dict(
#               [(e.gpstime, reverse("event-detail", args=[e.graceid()], request=request))
#                   for e in event.neighbors()]),
            "neighbors" : reverse("neighbors", args=[graceid], request=request),
            "log"   : reverse("eventlog-list", args=[graceid], request=request),
            "files" : reverse("files", args=[graceid], request=request),
            "filemeta" : reverse("filemeta", args=[graceid], request=request),
            "labels" : reverse("labels", args=[graceid], request=request),
            "self"  : reverse("event-detail", args=[graceid], request=request),
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
    parser_classes = (LigoLwParser,)
    #parser_classes = (parsers.MultiPartParser,)
    serializer_class = EventSerializer
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
        fdest = open(uploadDestination, 'w')
        # Save uploaded file into user private area.
        for chunk in f.chunks():
            fdest.write(chunk)
        fdest.close()

        # Extract Info from uploaded data
        try:
            handle_uploaded_data(event, uploadDestination)
            event.submitter = request.ligouser
        except:
            return Response("Bad Data",
                    status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)

#==================================================================
# Neighbors

class EventNeighbors(APIView):
    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        if request.QUERY_PARAMS.has_key('delta'):
            delta = request.QUERY_PARAMS['delta']
            if delta.find(',') < 0:
                delta = delta2 = int(delta)
            else:
                delta , delta2 = map(int, delta.split(','))
            neighbors = event.neighbors(delta=delta, delta2=delta2)
        else:
            neighbors = event.neighbors()
        neighbors = [eventToDict(neighbor, request=request)
                    for neighbor in neighbors]
        return Response({
                'neighbors' : neighbors,
                'delta' : (5,5), # XXX get from Event, or request.
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
            labels = [map(
                lambda x: labelToDict(x,request=request),
                event.labelling_set.all())]
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
        return Response("Not Implemented", status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, graceid, label):
        return Response("Not Implemented", status=status.HTTP_501_NOT_IMPLEMENTED)

#==================================================================
# EventLog

# Janky serialization
def eventLogToDict(log, n=None, request=None):
    # XXX Messy.  n should not be here but in the model.
    if (n is None) and request:
        uri = request.build_absolute_uri()
    elif n is not None and request:
        uri = reverse("eventlog-detail",
                args=[log.event.graceid(), n],
                request=request)
    else:
        uri = None
    return {
                "comment" : log.comment,
                "created" : log.created,
                "issuer"  : log.issuer.name,
                "self"    : uri,
           }

class EventLogList(APIView):
    """Event Log List Resource

    POST param 'message'
    """
    authentication_classes = (LigoAuthentication,)

    def get(self, request, graceid):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Event does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        logset = event.eventlog_set.order_by("created")
        count = logset.count()
        rv = [ eventLogToDict(log, n, request)
                for (n, log) in zip(range(0,count+2), logset.iterator()) ]
        return Response(rv)

    def post(self, request, graceid):
        event = Event.getByGraceid(graceid)
        message = request.DATA.get('message')
        logentry = EventLog(
                event=event,
                issuer=request.ligouser,
                comment=message)
        logset = event.eventlog_set.order_by("created")
        n = len(logset)
        logentry.save()
        rv = eventLogToDict(logentry, n, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        return response

class EventLogDetail(APIView):
    authentication_classes = (LigoAuthentication,)

    def get(self, request, graceid, n):
        try:
            event = Event.getByGraceid(graceid)
        except Event.DoesNotExist:
            # XXX Real error message.
            return Response("Log Entry Not Found",
                    status=status.HTTP_404_NOT_FOUND)
        rv = event.eventlog_set.order_by("created").all()[int(n)]
        return Response(eventLogToDict(rv, request=request))

#==================================================================
# Root Resource

class GracedbRoot(APIView):
    """
        Root of the Gracedb REST API
    """
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

        labels = reverse('labels', args=["G1200", "thelabel"], request=request)
        labels = labels.replace("G1200", "{graceid}")
        labels = labels.replace("thelabel", "{label}")

        return Response({
            "resources" : {
                "events" : reverse("event-list", request=request),
            },
            "resource-templates" : {
                "event-template" : detail,
                "event-log-template" : log,
                "event-files-template" : files,
                "event-filemeta-template" : filemeta,
                "event-label-template" : labels,
            },
                "groups" : [group.name for group in Group.objects.all()],
                "analysis-types" : dict(Event.ANALYSIS_TYPE_CHOICES),
                "labels" : [label.name for label in Label.objects.all()],
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

        response = HttpResponse(json.dumps(rv), content_type="application/json")
    elif os.path.isdir(filepath):
        response = HttpResponseForbidden("%s is a directory" % filename)
    else:
        response = HttpResponseServerError("Should not happen.")

    return response

class Files(APIView):
    """Files Resource"""

    authentication_classes = (LigoAuthentication,)
    parser_classes = (parsers.MultiPartParser,)

    def get(self, request, graceid, filename=None):
        # Do not let filename be None.  That messes up later os.path.join
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
            response = HttpResponse(open(filepath, "r"), content_type="application/octet-stream")
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
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

        # Construct the file path just as Brian does above.
        general = False
        if filename.startswith("general/"):
            filename = filename[len("general/"):]
            general = True

        filepath = os.path.join(event.datadir(general), filename)

        if not os.path.exists(filepath):
            # Awesome.  The thing does not exist.  This is the first time a file
            # by this name is being uploaded.  
            # Write the file as "filename,0".
            linkpath = filepath
            filepath += ',0'
            filename += ',0'
            fdest = open(filepath, 'w')
            # Check out line 392 in the client.  I think the key name for the file is 'upload'
            f = request.FILES['upload']
            for chunk in f.chunks(): 
                fdest.write(chunk)
            fdest.close()

            # Make a relative symlink.
            os.symlink(filename,linkpath)

            rv = {}
            rv['permalink'] = reverse("files", args=[graceid, filename], request=request)
            response = Response(rv, status=status.HTTP_201_CREATED)

        elif os.path.islink(filepath):
            # Great. The thing is a symlink. We can do our version-y stuff now.

            # Read contents of directory.  Establish the number of existing versions.
            # All we need is the bare filename (i.e., not the full path)
            filedir = event.datadir(general)
            lastVersion = 0
            for dirname, dirnames, filenames in os.walk(filedir):
                for fname in filenames:
                    if fname.find(',') > 0:
                        if fname.split(',')[0] == filename:
                            lastVersion = max(lastVersion,int(fname.split(',')[1]))
            
            linkpath = filepath # Set the link path to the original file path.
            notOpenYet = True
            failedAttempts = 0
            while notOpenYet:
                # find the new filename
                newFilename = filename + ',%d' % (lastVersion+1)
                # update the file path according to the new filename.
                filepath = os.path.join(filedir,newFilename)
                try:
                    # os.O_EXCL causes the open to fail if the file already exists.
                    fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0644)
                    fdest = os.fdopen(fd,"w")
                    notOpenYet = False
                except OSError as e:
                    if e.errno==errno.EACCES:
                        return HttpResponseForbidden("No permission to write to event directory.")
                    else:
                        # Note: could also check whether e.errno==errno.EEXIST
                        ++failedAttempts
                        if failedAttempts >= MAX_FAILED_OPEN_ATTEMPTS:
                            return HttpResponseServerError("Cannot open file for writing: %s" % e)
                        # Under race conditions, increment lastVersion.
                        if e.errno==errno.EACCES:
                            ++lastVersion 
            
            # Still with me? Then write the file.
            f = request.FILES['upload']
            for chunk in f.chunks(): 
                fdest.write(chunk)
            fdest.close()

            # Move the symlink, using os.rename to avoid race conditions. 
            tmplink = os.path.join(filedir,'tmplink')
            os.symlink(newFilename,tmplink)
            os.rename(tmplink,linkpath)
            
            rv = {}
            rv['permalink'] = reverse("files", args=[graceid, newFilename], request=request)
            response = Response(rv, status=status.HTTP_201_CREATED)

        elif os.path.isfile(filepath):
            # The thing is a file and not a symlink.  We will not allow a put request to the file
            # resource (for now, anyway).
            response = HttpResponseForbidden("%s is a file.  Versioning is not supported with legacy data.  Please change your filename to avoid clobbering." % filename)
        elif not filename:
            # Not good.  There's nothing we can do without a filename.
            response = HttpResponseBadRequest("Must have a filename for upload.")
        elif os.path.isdir(filepath):
            response = HttpResponseForbidden("%s is a directory" % filename)
        else:
            response = HttpResponseServerError("Should not happen.")

        return response

class FileMeta(APIView):
    """File Metadata Resource"""
    authentication_classes = (LigoAuthentication,)
    pass
