
from django.http import HttpResponse, HttpResponseNotFound
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.core.urlresolvers import reverse as django_reverse

from django.conf import settings
from django.utils.functional import wraps
from django.db import IntegrityError

import json

from django.contrib.auth.models import User, Permission
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from gracedb.models import Event, Group, Search, Pipeline, EventLog, Tag
from gracedb.models import EMGroup, EMBBEventLog, EMSPECTRUM
#from gracedb.models import EMObservation, EMFootprint
from gracedb.models import VOEvent
from view_logic import create_label, get_performance_info
from view_logic import _createEventFromForm
from view_logic import create_eel
from view_logic import create_emobservation
from view_utils import fix_old_creation_request
from view_utils import eventToDict, eventLogToDict, labelToDict
from view_utils import embbEventLogToDict, voeventToDict
from view_utils import emObservationToDict, skymapViewerEMObservationToDict
from view_utils import signoffToDict
from view_utils import reverse

from translator import handle_uploaded_data
from forms import CreateEventForm
from permission_utils import user_has_perm, filter_events_for_user, is_external
from permission_utils import check_external_file_access
from guardian.models import GroupObjectPermission

from throttles import EventCreationThrottle, AnnotationThrottle

from alert import issueAlertForUpdate
from buildVOEvent import buildVOEvent, VOEventBuilderException

import os
import urllib
import shutil
import exceptions

from utils.vfile import VersionedFile

# 
# for checking queries in the evnet that the user is external
#
from view_utils import BadFARRange, check_query_far_range
from query import parseQuery

##################################################################

REST_FRAMEWORK_SETTINGS = getattr(settings, 'REST_FRAMEWORK', {})
PAGINATE_BY = REST_FRAMEWORK_SETTINGS.get('PAGINATE_BY', 10)

##################################################################
# rest_framework
from rest_framework import serializers, status
from rest_framework.response import Response
#from rest_framework.renderers import JSONRenderer, JSONPRenderer
#from rest_framework.renderers import YAMLRenderer, XMLRenderer
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework import parsers      # YAMLParser, MultiPartParser
from rest_framework.parsers import DataAndFiles

from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework import authentication
from rest_framework.views import APIView

MAX_FAILED_OPEN_ATTEMPTS = 5

from forms import SimpleSearchForm


##################################################################
# Stuff for the LigoLwRenderer
from glue.ligolw import ligolw
# lsctables MUST be loaded before utils.
from glue.ligolw import utils
from glue.ligolw.utils import ligolw_add
from glue.ligolw.ligolw import LIGOLWContentHandler
from glue.ligolw.lsctables import use_in
import StringIO

use_in(LIGOLWContentHandler)

# 
# We do not want to handle authentication here because it has already
# been taken care of by Apache/Shib or Apache/mod_ssl. Moreover the 
# auth middleware has already added a user to the request object. To
# play well with the django rest framework, we need to pretend like we
# authenticated the user. Remember that the request object here is a 
# *wrapped* version of the Django request, so we have to dig inside it
# for the user.
#
class LigoAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        user = None
        try: 
            user = request._request.user
        except:
            pass                    

        if isinstance(user, User):
            return (user, None)
        else:
            raise exceptions.AuthenticationFailed("Bad user")

#
# A custom permission class for the EventDetail view. 
#
class IsAuthorizedForEvent(BasePermission):
    def has_object_permission(self, request, view, obj):
        # "Safe methods" only require view permission.
        if request.method in SAFE_METHODS:
            shortname = 'view'
        # "Unsafe methods" require change permissions on the event.
        # Note that DELETE is only implemented for event-log-tag 
        # relationships.
        elif request.method in ['PUT','POST','DELETE']:
            shortname = 'change'
        else:
            return False
        return user_has_perm(request.user, shortname, obj)        
#
# A custom permission class for event creation
#
class IsAuthorizedForPipeline(BasePermission):
    def has_object_permission(self, request, view, obj):
        return user_has_perm(request.user, "populate_pipeline", obj)        

#
# A wrapper to get an event by the graceid in the arguments 
# list and then check permission on it.
# IsAuthorizedForEvent must be in the permission_classes.
#
def event_and_auth_required(view):
    @wraps(view)
    def inner(self, request, graceid, *args, **kwargs):
        try:
            event = Event.getByGraceid(graceid)
            self.check_object_permissions(request, event)
        except Event.DoesNotExist:
            return HttpResponseNotFound("Event not found.")
        return view(self, request, event, *args, **kwargs)
    return inner

def pipeline_auth_required(view):
    @wraps(view)
    def inner(self, request, *args, **kwargs):
        group_name = request.data.get('group', None)
        if not group_name=='Test':
            try:
                pipeline = Pipeline.objects.get(name=request.data['pipeline'])
            except:
                return Response({'error': "Please provide a valid pipeline."}, 
                    status = status.HTTP_400_BAD_REQUEST)
            self.check_object_permission(request, pipeline)
        return view(self, request, *args, **kwargs)
    return inner

#
# A wrapper to access a particular eventlog message based
# on the log number N passed in.
#
def eventlog_required(view):
    @wraps(view)
    def inner(self, request, event, n, *args, **kwargs):
        try:
            eventlog = event.eventlog_set.filter(N=n)[0]
        except:
            return Response("Log does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        return view(self, request, event, eventlog, *args, **kwargs)
    return inner

#
# A wrapper to access a particular group based on the group name.
#
def group_required(view):
    @wraps(view)
    def inner(self, request, event, group_name, *args, **kwargs):
        try:
            group = AuthGroup.objects.get(name=str(group_name))
        except:
            return Response("Group does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        return view(self, request, event, group, *args, **kwargs)
    return inner

#
# A wrapper to access a permission based on the shortname and the event
#
def event_perm_object_required(view):
    @wraps(view)
    def inner(self, request, event, group, perm_shortname, *args, **kwargs):

        # We have to find the thing before we can delete it.
        # Get the content type for this event.
        model_name = event.__class__.__name__.lower()

        # Find the permission
        codename = perm_shortname + '_' + model_name
        try:
            permission = Permission.objects.get(codename=codename)
        except Permission.DoesNotExist:
            return Response("Permission not found.", 
                status=status.HTTP_404_NOT_FOUND)
        return view(self, request, event, group, permission, *args, **kwargs)
    return inner

#class EventSerializer(serializers.ModelSerializer):
#    # Overloaded fields.
#    group = serializers.CharField(source="group.name")
#    submitter = serializers.CharField(source="submitter.name")
#    graceid = serializers.Field(source="graceid")
#    analysisType = serializers.Field(source="get_analysisType_display")
#
#    # New fields.
#    labels = serializers.SerializerMethodField('get_labels') 
#    links = serializers.SerializerMethodField('get_links')
#
#    class Meta:
#        model = Event
#        fields = ('submitter', 'created', 'group', 'graceid',
#                  'analysisType', 'gpstime', 'instruments',
#                  'nevents', 'far', 'likelihood', 'labels',
#                  'links',)
#
#    def get_labels(self,obj):
#        request = self.context['request']
#        graceid = obj.graceid()
#        return dict([
#            (labelling.label.name,
#                reverse("labels",
#                    args=[graceid, labelling.label.name],
#                    request=request))
#            for labelling in obj.labelling_set.all()])
#
#    def get_links(self,obj):
#        request = self.context['request']
#        graceid = obj.graceid()
#        return {
#            "neighbors" : reverse("neighbors", args=[graceid], request=request),
#            "log"   : reverse("eventlog-list", args=[graceid], request=request),
#            "files" : reverse("files", args=[graceid], request=request),
#            "filemeta" : reverse("filemeta", args=[graceid], request=request),
#            "labels" : reverse("labels", args=[graceid], request=request),
#            "self"  : reverse("event-detail", args=[graceid], request=request),
#            "tags"  : reverse("eventtag-list", args=[graceid], request=request),
#            }

class EventLogSerializer(serializers.ModelSerializer):
    """docstring for EventLogSerializer"""
    comment =  serializers.CharField(required=True, max_length=200)
    class Meta:
        model = EventLog
        fields = ('comment', 'issuer', 'created')
#==================================================================
# Custom renderers and various accoutrements

class MissingCoinc(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Event list contained event(s) for which no coinc exists."  
    def __init__(self, detail=None):
        self.detail = detail or self.default_detail 
    def __str__(self):
        return repr(self.detail)

class CoincAccess(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Problem reading coinc file."
    def __init__(self, detail=None):
        self.detail = detail or self.default_detail 
    def __str__(self):
        return repr(self.detail)

def assembleLigoLw(data):
    if 'events' in data.keys():
        eventDictList = data['events']
    else:
        # There is only one event.
        eventDictList = [data,]
    xmldoc = ligolw.Document()
    for e in eventDictList:
        fname = os.path.join(e.datadir(), "coinc.xml")
        if not os.path.exists(fname):
            raise MissingCoinc
        elif not os.access(fname, os.R_OK):
            raise CoincAccess
        utils.load_filename(fname, xmldoc=xmldoc, contenthandler=LIGOLWContentHandler)
    ligolw_add.reassign_ids(xmldoc)
    ligolw_add.merge_ligolws(xmldoc)
    ligolw_add.merge_compatible_tables(xmldoc)
    return xmldoc

class LigoLwRenderer(BaseRenderer):
    media_type = 'application/xml'
    format = 'xml'

    def render(self, data, media_type=None, renderer_context=None):
        # XXX If there was an error, we will return the error message
        # in plain text, effectively ignoring the accepts header. 
        # Somewhat irregular?
        if 'error' in data.keys():
            return data['error']
        
        xmldoc = assembleLigoLw(data)
        # XXX Aaargh! Just give me the contents of the xml doc. Annoying.
        output = StringIO.StringIO()
        xmldoc.write(output)
        return output.getvalue()

class TSVRenderer(BaseRenderer):
    media_type = 'text/tab-separated-values'
    format = 'tsv'

    def render(self, data, media_type=None, renderer_context=None):
        if 'error' in data.keys():
            return data['error']

        accessFun = {
            "labels" : lambda e: \
                ",".join(e['labels'].keys()),
            "dataurl" : lambda e: e['links']['files'],
        }
        def defaultAccess(e,a):
            if a.find('.') < 0:
                return str(e.get(a,""))
            rv = e
            attrs = a.split('.')
            while attrs and rv:
                rv = rv.get(attrs[0],"")
                attrs = attrs[1:]
            return str(rv)

        #defaultColumns = "graceid,labels,group,analysisType,far,gpstime,created,dataurl"
        defaultColumns = "graceid,labels,group,pipeline,search,far,gpstime,created,dataurl"
        # XXX Que monstroso!
        columns = renderer_context.get('kwargs', None).get('columns', None)
        if not columns:
            columns = defaultColumns
        else:
            columns = columns.replace('DEFAULTS',defaultColumns)
        columns = columns.split(',')

        header = "#" + "\t".join(columns)
        outTable = [header]
        for e in data['events']:
            row = [ accessFun.get(column, lambda e: defaultAccess(e,column))(e) for column in columns ]
            outTable.append("\t".join(row))
        outTable = "\n".join(outTable)
       
        return outTable

#==================================================================
# Events

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
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForPipeline)
    parser_classes = (parsers.MultiPartParser,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer, LigoLwRenderer, TSVRenderer,)
    throttle_classes = (EventCreationThrottle,)

    def get(self, request, *args, **kwargs):

        """I am the GET docstring for EventList"""
        query = request.query_params.get("query")
        count = request.query_params.get("count", PAGINATE_BY)
        start = request.query_params.get("start", 0)
        sort = request.query_params.get("sort", "-created")
        columns = request.query_params.get("columns", "")

        events = Event.objects
        if query:
            # If the user is external, we must check to make sure that any query on FAR
            # value is within the safe range.
            if is_external(request.user):
                try:
                    check_query_far_range(parseQuery(query))
                except BadFARRange:
                    msg = 'FAR query out of range, upper limit must be below %s' % settings.VOEVENT_FAR_FLOOR
                    d = {'error': msg }
                    return Response(d,status=status.HTTP_400_BAD_REQUEST)

            form = SimpleSearchForm(request.GET)
            if form.is_valid():
                events = form.cleaned_data['query']
            else:
                d = {'error': 'Invalid query' }
                return Response(d,status=status.HTTP_400_BAD_REQUEST)

        events = filter_events_for_user(events, request.user, 'view')

        events = events.order_by(sort).select_subclasses()

        start = int(start)
        count = int(count)
        numRows = events.count()

        # Fail if the output format is ligolw, and there are more than 1000 events
        if request.accepted_renderer.format == 'xml' and numRows > 1000:
            d = {'error': 'Too many events.' }
            return Response(d, status=status.HTTP_400_BAD_REQUEST)

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

        response = Response(rv)

        # XXX Next, we try finalizing and rendering the response. According to
        # the django rest framework docs (see .render() in
        # http://django-rest-framework.org/api-guide/responses.html), this is
        # unusual. But we want to handle the exceptions raised during rendering 
        # ourselves.  And that is not easy to do if the exceptions are raised 
        # somewhere deep inside the entrails of django.
        # NOTE: This will not result in two calls to render().  Django will check
        # the _is_rendered property of the response before attempteding to render.
        # I have tested this by putting logging commands inside the custom renderers.
        try:
            if request.accepted_renderer.format == 'xml':
                response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
            # XXX Get the columns into renderer_context. Bizarre? Why, yes.
            setattr(self, 'kwargs', {'columns': columns})
            # NOTE When finalize_response is calld in its natural habitat, the 
            # args and kwargs are the same as those passed to the 'handler', i.e., 
            # the function we are presently inside.
            response = self.finalize_response(request, response, *args, **kwargs)
            response.render()
        except Exception, e:
            try:
                status_code = e.status_code
            except:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({'error': str(e)}, status=status_code)

        return response

    #@pipeline_auth_required
    def post(self, request, format=None):
        # XXX Deal with POSTs coming in from the old client.
        # Eventually, we will want to get rid of this check and just let it fail.
        rv = {}
        rv['warnings'] = []
        if 'type' in request.data:
            request = fix_old_creation_request(request)
            rv['warnings'] += ['It looks like you are using the old GraceDB client (v<=1.14). ' + \
                             'Please update! This will eventually stop working.']

        # Check user authorization for pipeline. 
        # XXX This is a temporary hack until they roll out the new client.
        group_name = request.data.get('group', None) 
        if not group_name=='Test':
            try:
                pipeline = Pipeline.objects.get(name=request.data['pipeline'])
            except:
                return Response({'error': "Please provide a valid pipeline."},
                    status = status.HTTP_400_BAD_REQUEST)
            if not user_has_perm(request.user, "populate", pipeline):
                return HttpResponseForbidden("You don't have permission on this pipeline.")
        
        # The following looks a bit funny but it is actually necessary. The 
        # django form expects a dict containing the POST data as the first
        # arg, and a dict containing the FILE data as the second. In the 
        # django-restframework, however, both are in request.data
        form = CreateEventForm(request.data, request.data)
        if form.is_valid():
            event, warnings = _createEventFromForm(request, form)
            if event:
                rv.update(eventToDict(event, request=request))
                rv['warnings'] += warnings
                response = Response(rv, status=status.HTTP_201_CREATED)
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

class EventDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    #parser_classes = (LigoLwParser, RawdataParser)
    parser_classes = (parsers.MultiPartParser,)
    #serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer, LigoLwRenderer,)

    form = CreateEventForm

    @event_and_auth_required
    def get(self, request, event):
        #response = Response(self.serializer_class(event, context={'request': request}).data)
        response = Response(eventToDict(event, request=request))

        response["Cache-Control"] = "no-cache"

        # XXX Next, we try finalizing and rendering the response. According to
        # the django rest framework docs (see .render() in
        # http://django-rest-framework.org/api-guide/responses.html), this is
        # unusual. But we want to handle the exceptions raised during rendering 
        # ourselves.  And that is not easy to do if the exceptions are raised 
        # somewhere deep inside the entrails of django.
        # NOTE: This will not result in two calls to render().  Django will check
        # the _is_rendered property of the response before attempteding to render.
        # I have tested this by putting logging commands inside the custom renderers.
        try:
            if request.accepted_renderer.format == 'xml':
                response['Content-Disposition'] = 'attachment; filename=gracedb-event.xml'
            # NOTE When finalize_response is calld in its natural habitat, the 
            # args and kwargs are the same as those passed to the 'handler', i.e., 
            # the function we are presently inside.
            response = self.finalize_response(request, response)
            response.render()
        except Exception, e:
            try:
                status_code = e.status_code
            except:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({'error': str(e)}, status=status_code)

        return response

    @event_and_auth_required
    def put(self, request, event):
        """ I am a doc.  Do I not get put anywhere? """

        # An additional authorization check: Are we dealing with the original submitter?
        try:
            if request.user != event.submitter:
                msg = "You (%s) Them (%s)" % (request.user, event.submitter)
                return HttpResponseForbidden("You did not create this event. %s" %msg)
        except Exception, e:
            return Response(str(e))

#       messages = []
#       if event.group.name != request.data['group']:
#           messages += [
#                   "Existing event group ({0}) does not match "
#                   "replacement event group ({1})".format(
#                       event.group.name, request.data['group'])]
#       if event.analysisType != request.data['type']:
#           messages += [
#                   "Existing event type ({0}) does not match "
#                   "replacement event type ({1})".format(
#                       event.analysisType, request.data['type'])]
#       if messages:
#           return Response("\n".join(messages),
#                   status=status.HTTP_400_BAD_REQUEST)

        # XXX handle duplicate file names.
        f = request.data['eventFile']
        uploadDestination = os.path.join(event.datadir(), f.name)
        fdest = VersionedFile(uploadDestination, 'w')
        #for chunk in f.chunks():
        #    fdest.write(chunk)
        #fdest.close()
        shutil.copyfileobj(f, fdest)
        fdest.close()

        # Extract Info from uploaded data
        try:
            handle_uploaded_data(event, uploadDestination)
            event.submitter = request.user
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
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    # XXX Since this returns an event list, we could add the LigoLW
    # and TSV renderers.
    @event_and_auth_required
    def get(self, request, event):
        if request.query_params.has_key('neighborhood'):
            delta = request.query_params['neighborhood']
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
        neighbors = filter_events_for_user(neighbors, request.user, 'view')

        neighbors = [eventToDict(neighbor, request=request)
                    for neighbor in neighbors]
        return Response({
                'neighbors' : neighbors,
                'neighborhood' : neighborhood,
                'numRows' : len(neighbors),
                'links' : {
                    'self': request.build_absolute_uri(),
                    'event': reverse("event-detail", args=[event.graceid()], request=request),
                    }
                })

#==================================================================
# Labels

# XXX NOT FINISHED

class EventLabel(APIView):
    """Event Label"""
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, label):
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

    @event_and_auth_required
    def put(self, request, event, label):
        try:
            rv = create_label(event, request, label)
        except ValueError, e:
            return Response(e.message,
                        status=status.HTTP_400_BAD_REQUEST)

        return Response(rv, status=status.HTTP_201_CREATED)

    def delete(self, request, graceid, label):
        return Response("Not Implemented", status=status.HTTP_501_NOT_IMPLEMENTED)

#==================================================================
# EventLog

class EventLogList(APIView):
    """Event Log List Resource

    POST param 'message'
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        logset = event.eventlog_set.order_by("created","N")

        # Filter log messages for external users.
        if is_external(request.user):
            logset = logset.filter(tag__name=settings.EXTERNAL_ACCESS_TAGNAME)

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


    @event_and_auth_required
    def post(self, request, event):
        message = request.data.get('message')
        tagnames = request.data.get('tagname', None)
        # Convert tagnames from comma separated list.
        if tagnames:
            tagnames = tagnames.split(',')
        else:
            tagnames = []

        try:
            uploadedFile = request.data['upload'] 
            self.check_object_permissions(self.request, event)
        except:
            uploadedFile = None

        filename = None
        file_version = None
        if uploadedFile:
            filename = uploadedFile.name 
            filepath = os.path.join(event.datadir(), filename)

            try:
                # Open / Write the file.
                fdest = VersionedFile(filepath, 'w')
                for chunk in uploadedFile.chunks(): 
                    fdest.write(chunk)
                fdest.close()
                # Ascertain the version assigned to this particular file.
                file_version = fdest.version
            except Exception, e:
                # XXX This needs some thought.
                response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        logentry = EventLog(
                event=event,
                issuer=request.user,
                comment=message,
                filename=filename,
                file_version=file_version)
        #logset = event.eventlog_set.order_by("created","N")
        try:
            logentry.save()
        except Exception as e:
            # Since this is likely due to race conditions, we will return 503
            return Response("Failed to save log entry: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # XXX For external users, make sure that the new log entry is tagged so
        # they'll be able to see it later.
        if is_external(request.user):
            if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                tagnames.append(settings.EXTERNAL_ACCESS_TAGNAME)

        tw_dict = {}
        if tagnames and len(tagnames):
            for tagname in tagnames:
                n = logentry.N
                tmp = EventLogTagDetail()
                retval = tmp.put(request, event.graceid(), n, tagname) 
                # XXX This seems like a bizarre way of getting an error message out.
                if retval.status_code != 201:
                    tw_dict = {'tagWarning': 'Error creating tag %s.' % tagname }
                    #response['tagWarning'] = 'Error creating tag %s.' % tagname
                    
        # Serialize the event log object *after* adding tags!
        rv = eventLogToDict(logentry, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        if 'tagWarning' in tw_dict.keys():
            response['tagWarning'] = tw_dict['tagWarning']


        # Issue alert.
        description = "LOG: "
        fname = ""
        if uploadedFile:
            description = "UPLOAD: '%s' " % uploadedFile.name
            fname = uploadedFile.name
        issueAlertForUpdate(event, description+message, doxmpp=True, 
            filename=fname, serialized_object=rv)

        return response

class EventLogDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog):
        # XXX Access control to log messages for external users.
        if is_external(request.user):
            tagnames = [t.name for t in eventlog.tag_set.all()]
            if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                msg = 'You do not have permission to view this log message.'
                return HttpResponseForbidden(msg)
        return Response(eventLogToDict(eventlog, request=request))


#==================================================================
# EMBBEventLog (EEL)

class EMBBEventLogList(APIView):
    """EMBB Event Log List Resource

    POST param 'message'
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        eel_set = event.embbeventlog_set.order_by("created","N")
        count = eel_set.count()

        eel = [ embbEventLogToDict(eel, request)
                for eel in eel_set.iterator() ]

        rv = {
                'start': 0,
                'numRows' : count,
                'links' : {
                    'self' : request.build_absolute_uri(),
                    'first' : request.build_absolute_uri(),
                    'last' : request.build_absolute_uri(),
                    },
                'embblog' : eel,
             }
        return Response(rv)

    @event_and_auth_required
    def post(self, request, event):
        try:
            eel = create_eel(request.data, event, request.user)
        except ValueError, e:
            return Response("%s" % str(e), status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError, e:
            return Response("Failed to save EMBB entry: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception, e:
            return Response("Problem creating EEL: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = embbEventLogToDict(eel, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']

        # Issue alert.
        description = "New EMBB log entry."
        issueAlertForUpdate(event, description, doxmpp=True,
            filename="", serialized_object=rv)

        return response

class EMBBEventLogDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, n):
        try:
            rv = event.embbeventlog_set.filter(N=n)[0]
        except:
            return Response("Log Message Not Found",
                    status=status.HTTP_404_NOT_FOUND)

        return Response(embbEventLogToDict(rv, request=request))


#==================================================================
# EMObservation (EMO)

class EMObservationList(APIView):
    """EMObservation Record List Resource

    POST param 'message'
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        emo_set = event.emobservation_set.order_by("created","N")
        count = emo_set.count()

        # XXX Note the following hack.
        # If this JSON information is requested for skymapViewer, use a different
        # representation for backwards compatibility.
        if 'skymapViewer' in request.query_params.keys():
            emo = [ skymapViewerEMObservationToDict(emo, request)
                    for emo in emo_set.iterator() ]

            rv = {
                    'start': 0,
                    'numRows' : count,
                    'links' : {
                        'self' : request.build_absolute_uri(),
                        'first' : request.build_absolute_uri(),
                        'last' : request.build_absolute_uri(),
                        },
                    'embblog' : emo,
                 }

        else:
            emo = [ emObservationToDict(emo, request)
                    for emo in emo_set.iterator() ]

            rv = {
                    'start': 0,
                    'numRows' : count,
                    'links' : {
                        'self' : request.build_absolute_uri(),
                        'first' : request.build_absolute_uri(),
                        'last' : request.build_absolute_uri(),
                        },
                    'observations' : emo,
                 }
        return Response(rv)

    @event_and_auth_required
    def post(self, request, event):
        try:
            emo = create_emobservation(request, event)
        except ValueError, e:
            return Response("%s" % str(e), status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError, e:
            return Response("Failed to save EMBB observation record: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception, e:
            return Response("Problem creating EMBB Observation: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = emObservationToDict(emo, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        return response

class EMObservationDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, n):
        try:
            rv = event.emobservation_set.filter(N=n)[0]
        except:
            return Response("Observation record not nound",
                    status=status.HTTP_404_NOT_FOUND)

        return Response(emObservationToDict(rv, request=request))


#==================================================================
# Tags

# XXX This serializer should be moved to view_utils along with the others.
def tagToDict(tag, columns=None, request=None, event=None, n=None):
    """Convert a tag to a dictionary.
       Output depends on the level of specificity.
    """

    rv = {}
    rv['name'] = tag.name
    rv['displayName'] = tag.displayName
    if event:
        # XXX Technically, this list should be filtered based on whether the
        # user is external and has access to the logs. I don't think this is 
        # a big deal, though.
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
        tag_dict = {}
        for tag in Tag.objects.all():
            tag_dict[tag.name] = { 
                'displayName': tag.displayName,
                'blessed': tag.name in settings.BLESSED_TAGS
            }
        rv = {
#                 'tags' : [ reverse("tag-detail", args=[tag.name],
#                                    request=request)
#                            for tag in Tag.objects.all() ]
#                For now, we just output the tag names, since we don't know what 
#                tag-detail should look like.
#                 'tags' : [ tag.name for tag in Tag.objects.all() ]
                  'tags' : tag_dict,
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
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event):
        # Return a list of links to all tags for this event.
        # XXX Technically, this list should be filtered based on whether the
        # user is external and has access to the logs. I don't think this is 
        # a big deal, though.
        rv = {
                'tags' : [ reverse("eventtag-detail",args=[event.graceid(),
                                   tag.name],
                                   request=request)
                           for tag in event.getAvailableTags()]
             }

        return Response(rv)

class EventTagDetail(APIView):
    """Event Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, tagname):
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
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog):
        rv = {
                'tags' : [ reverse("eventlogtag-detail",
                                    args=[event.graceid(), 
                                    eventlog.N, tag.name],
                                    request=request)
                           for tag in eventlog.tag_set.all()]
             }

        return Response(rv)

class EventLogTagDetail(APIView):
    """Event Log Tag Detail Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog, tagname):
        try:
            tag = eventlog.tag_set.filter(name=tagname)[0]
            # Serialize
            return Response(tagToDict(tag,event=event,n=eventlog.N,request=request))
        except:
            return Response("Tag not found.",status=status.HTTP_404_NOT_FOUND)

    @event_and_auth_required
    @eventlog_required
    def put(self, request, event, eventlog, tagname):
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
            # Check authorization
            if is_external(request.user) and tagname == settings.EXTERNAL_ACCESS_TAGNAME:
                if eventlog.issuer != request.user:
                    msg = "You do not have permission to add or remove this tag."
                    return HttpResponseForbidden(msg)            

            # Look for the tag.  If it doesn't already exist, create it.
            try:
                tag = Tag.objects.filter(name=tagname)[0]
            except:
                displayName = request.data.get('displayName')
                tag = Tag(name=tagname, displayName=displayName)
                tag.save()

            # Now add the log message to this tag.
            tag.eventlogs.add(eventlog)

            # Create a log entry to document the tag creation.
            msg = "Tagged message %s: %s " % (eventlog.N, tagname)
            logentry = EventLog(event=event,
                               issuer=request.user,
                               comment=msg)
            try:    
                logentry.save()
            except Exception as e:
                # Since the tag creation was successful, we'll return 201.
                return Response("Tag succesful, but failed to create log entry: %s" % str(e),
                     status=status.HTTP_201_CREATED)

            return Response("Tag created.",status=status.HTTP_201_CREATED)

    @event_and_auth_required
    @eventlog_required
    def delete(self, request, event, eventlog, tagname):
        # Check authorization
        if is_external(request.user) and tagname == settings.EXTERNAL_ACCESS_TAGNAME:
            if eventlog.issuer != request.user:
                msg = "You do not have permission to add or remove this tag."
                return HttpResponseForbidden(msg)            

        try:
            tag = eventlog.tag_set.filter(name=tagname)[0]
            tag.eventlogs.remove(eventlog)

            # Is the tag empty now?  If so we can delete it.
            if not tag.eventlogs.all():
                tag.delete()

            # Create a log entry to document the tag creation.
            msg = "Removed tag %s for message %s. " % (tagname, eventlog.N)
            logentry = EventLog(event=event,
                               issuer=request.user,
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
# Permission Resources

def groupeventpermissionToDict(gop, event, request=None):
    """Convert a group object permission to a dictionary.
       Output depends on the level of specificity.
    """

    rv = {}
    rv['group'] = gop.group.name
    rv['graceid'] = event.graceid()
    perm_shortname = gop.permission.codename.split('_')[0]
    rv['permission'] = perm_shortname
    # We want a link to the self only.  End of the line.
    rv['links'] = {
                    "self" : reverse("groupeventpermission-detail",
                                     args=[event.graceid(),gop.group.name,perm_shortname],
                                     request=request)
                  }
    return rv

def getContentType(event):
    model_name = event.__class__.__name__.lower()
    return ContentType.objects.get(app_label='gracedb', model=model_name)

class EventPermissionList(APIView):
    """Event Permission List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event):
        # Get all the GroupObjectPermission objects for this event
        gops = GroupObjectPermission.objects.filter(content_type=getContentType(event), object_pk=event.id)
        # Create a set of distinct groups from them
        groups = set([gop.group for gop in gops])
        rv = {}
        links = {}
        rv['links'] = links
        links['self'] = request.build_absolute_uri()
        out_dict = {}
        links['groupeventpermissions'] = out_dict
        for group in groups:
            out_dict[group.name] = reverse("groupeventpermission-list", 
                args=[event.graceid(),group.name], request=request) 
        return Response(rv, status=status.HTTP_200_OK)            

class GroupEventPermissionList(APIView):
    """Group Event Permission List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @group_required
    def get(self, request, event, group):
        # Get all the GroupObjectPermission objects for this event and group
        gops = GroupObjectPermission.objects.filter(content_type=getContentType(event), 
            object_pk=event.id, group=group)
        rv = {}
        links = {}
        rv['links'] = links
        links['self'] = request.build_absolute_uri()
        rv['groupeventpermissions'] = [groupeventpermissionToDict(gop,event,request) for gop in gops] 
        return Response(rv, status=status.HTTP_200_OK)            

class GroupEventPermissionDetail(APIView):
    """Group Event Permission List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @group_required
    @event_perm_object_required
    def get(self, request, event, group, permission):
        # Get the GroupObjectPermission object
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=getContentType(event),
                object_pk=event.id, 
                group=group,
                permission=permission)        
            # Add this gop to the return dictionary
        except GroupObjectPermission.DoesNotExist:
            return Response("GroupObjectPermission not found.", 
                status=status.HTTP_404_NOT_FOUND)
        rv = {}
        links = {}
        rv['links'] = links
        links['self'] = request.build_absolute_uri()
        rv['groupeventpermission'] = groupeventpermissionToDict(gop,event,request)
        return Response(rv, status=status.HTTP_200_OK)            

    #
    # This adds a new permission to the group.  Idempotent
    # 
    @event_and_auth_required
    @group_required
    @event_perm_object_required
    def put(self, request, event, group, permission):
        if not request.user.has_perm("guardian.add_groupobjectpermission"):
            return HttpResponseForbidden("You don't have permission to change permission objects.")

        # Get or create the GroupObjectPermission object
        try:
            gop, created = GroupObjectPermission.objects.get_or_create(
                content_type=getContentType(event),
                object_pk=event.id, 
                group=group,
                permission=permission)        
            event.refresh_perms()
            # Add this gop to the return dictionary

            # XXX if the event is a subclass, we need to create perms on the
            # underlying event as well.
            # XXX Is this bad? It sort of feels like a side-effect.
            if not type(event) is Event:
                # how to get the permission object?
                shortname = permission.codename.split('_')[0]
                underlying_event = Event.objects.get(id=event.id)
                underlying_model = underlying_event.__class__.__name__.lower()
                codename = shortname + '_' + underlying_model
                try:
                    underlying_permission = Permission.objects.get(codename=codename)
                except Permission.DoesNotExist:
                    msg = "Problem creating permission: Could not find underlying event perm."
                    return Response(msg, status = status.HTTP_500_INTERNAL_SERVER_ERROR) 
                ugop, ucreated = GroupObjectPermission.objects.get_or_create(
                    content_type=getContentType(underlying_event),
                    object_pk=underlying_event.id, 
                    group=group,
                    permission=underlying_permission)        
                underlying_event.refresh_perms()

        except Exception, e:
            # We're gonna blame the user here.
            return Response("Problem creating permission: %" % str(e), 
                status=status.HTTP_400_BAD_REQUEST)
        rv = {}
        links = {}
        rv['links'] = links
        links['self'] = request.build_absolute_uri()
        rv['groupeventpermission'] = groupeventpermissionToDict(gop,event,request)
        status_code = status.HTTP_200_OK
        if created:
            status_code = status.HTTP_201_CREATED
        return Response(rv, status=status_code)

    #
    # This removes an existing permission from the group. Also idempotent.
    #
    @event_and_auth_required
    @group_required
    @event_perm_object_required
    def delete(self, request, event, group, permission):

        if not request.user.has_perm("guardian.delete_groupobjectpermission"):
            return HttpResponseForbidden("You don't have permission to change permission objects.")

        # Get the GroupObjectPermission object
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=getContentType(event),
                object_pk=event.id, 
                group=group,
                permission=permission)        
            gop.delete()
            event.refresh_perms()

            # XXX if the event is a subclass, we need to delete perms on the
            # underlying event as well.
            # XXX Is this bad? It sort of feels like a side-effect.
            if not type(event) is Event:
                # how to get the permission object?
                shortname = permission.codename.split('_')[0]
                underlying_event = Event.objects.get(id=event.id)
                underlying_model = underlying_event.__class__.__name__.lower()
                codename = shortname + '_' + underlying_model
                try:
                    underlying_permission = Permission.objects.get(codename=codename)
                except Permission.DoesNotExist:
                    msg = "Problem creating permission: Could not find underlying event perm."
                    return Response(msg, status = status.HTTP_500_INTERNAL_SERVER_ERROR) 
                ugop = GroupObjectPermission.objects.get(
                    content_type=getContentType(underlying_event),
                    object_pk=underlying_event.id, 
                    group=group,
                    permission=underlying_permission)        
                ugop.delete()
                underlying_event.refresh_perms()
           
        except GroupObjectPermission.DoesNotExist:
            return Response("GroupObjectPermission not found.", 
                status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            return Response("Problem deleting permission: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = {'message': 'Permission successfully deleted.'}
        return Response(rv, status=status.HTTP_200_OK)            

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
        voevent = reverse("voevent-list", args=["G1200"], request=request)
        voevent = voevent.replace("G1200", "{graceid}")
        embb = reverse("embbeventlog-list", args=["G1200"], request=request)
        embb = embb.replace("G1200", "{graceid}")
        emo = reverse("emobservation-list", args=["G1200"], request=request)
        emo = emo.replace("G1200", "{graceid}")

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

        signofflist = reverse("signoff-list", args=["G1200"], request=request)
        signofflist = signofflist.replace("G1200", "{graceid}")

        # XXX Need a template for the tag list?

        templates = {
                "event-detail-template" : detail,
                "voevent-list-template" : voevent,
                "event-log-template" : log,
                "emobservation-list-template": emo,
                "embb-event-log-template" : embb,
                "event-label-template" : labels,
                "files-template" : files,
                "filemeta-template" : filemeta,
                "tag-template" : tag,
                "taglist-template" : taglist,
                "signoff-list-template": signofflist,
                }

        return Response({
            "links" : {
                "events"      : reverse("event-list", request=request),
                "self"        : reverse("api-root", request=request),
                "performance" : reverse("performance-info", request=request),
                },
            "templates" : templates,
            "groups"    : [group.name for group in Group.objects.all()],
            "pipelines" : [pipeline.name for pipeline in Pipeline.objects.all()],
            "searches"  : [search.name for search in Search.objects.all()],
            # XXX Retained for compatibility with old clients (v<=1.14).
            # Should eventually be removed.
            "analysis-types" : dict(
                    (
                        ("LM",  "LowMass"),
                        ("HM",  "HighMass"),
                        ("GRB", "GRB"),
                        ("RD",  "Ringdown"),
                        ("OM",  "Omega"),
                        ("Q",   "Q"),
                        ("X",   "X"),
                        ("CWB", "CWB"),
                        ("MBTA", "MBTAOnline"), 
                        ("HWINJ", "HardwareInjection"),
                    ) 
                ),
            "em-groups"  : [g.name for g in EMGroup.objects.all()],
            "wavebands"      : dict(EMSPECTRUM),
            "eel-statuses"   : dict(EMBBEventLog.EEL_STATUS_CHOICES),
            "obs-statuses"   : dict(EMBBEventLog.OBS_STATUS_CHOICES),
            "voevent-types"  : dict(VOEvent.VOEVENT_TYPE_CHOICES),
           })

##################################################################
# Old.  Must support this.
def download(request, graceid, filename=""):
    # Do not filename to be None.  That messes up later os.path.join
    filename = filename or ""

    try:
        event = Event.getByGraceid(graceid)
        if not user_has_perm(request.user, 'view', event):
            return HttpResponseForbidden("Forbidden")
    except Event.DoesNotExist:
        return HttpResponseNotFound("Event not found")

    # If the user is external, check for authorization
    if is_external(request.user):
        if not check_external_file_access(event, filename):
            msg = "You do not have permission to view this file."
            return HttpResponseForbidden(msg)

    filepath = os.path.join(event.datadir(), filename)

    if not os.path.exists(filepath):
        response = HttpResponseNotFound("File does not exist")
    elif not os.access(filepath, os.R_OK):
        response = HttpResponseNotFound("File not readable")
    elif os.path.isfile(filepath):
        # get an actual file.
        content_type, encoding = VersionedFile.guess_mimetype(filepath)
        content_type = content_type or "application/octet-stream"
        # XXX encoding should probably not be ignored.

        # Get a pretty filename. Just strip off version info.
        # XXX This will break if you change the file-version naming convention
        # (by, for instance, using a different delimiter than a comma).
        try:
            ind = filename.index(',')
            pretty_filename = filename[:ind]
        except ValueError:
            pretty_filename = filename

        response = HttpResponse(open(filepath, "r"), content_type=content_type)
        if content_type == "application/octet-stream":
            #response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(filename)
            response['Content-Disposition'] = 'attachment; filename=%s' % pretty_filename
        else:
            response['Content-Disposition'] = 'inline; filename=%s' % pretty_filename
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

        response = HttpResponse(json.dumps(rv), content_type="application/json")
    elif os.path.isdir(filepath):
        response = HttpResponseForbidden("%s is a directory" % filename)
    else:
        response = HttpResponseServerError("Should not happen.")

    return response

class Files(APIView):
    """Files Resource"""

    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    #parser_classes = (RawdataParser,)
    parser_classes = (parsers.MultiPartParser,)

    @event_and_auth_required
    def get(self, request, event, filename=""):
        # Do not filename to be None.  That messes up later os.path.join
        filename = filename or ""
        graceid = event.graceid()

        filepath = os.path.join(event.datadir(), filename)

        if not os.path.exists(filepath):
            response = HttpResponseNotFound("File does not exist")
        elif not os.access(filepath, os.R_OK):
            response = HttpResponseNotFound("File not readable")
        elif os.path.isfile(filepath):
            # get an actual file.
            # If the user is external, check for authorization
            if is_external(request.user):
                if not check_external_file_access(event, filename):
                    msg = "You do not have permission to view this file."
                    return HttpResponseForbidden(msg)

            content_type, encoding = VersionedFile.guess_mimetype(filepath)
            content_type = content_type or "application/octet-stream"
            # XXX encoding should probably not be ignored.
            response = HttpResponse(open(filepath, "r"), content_type=content_type)
            if content_type == "application/octet-stream":
                # Double quotes are required to avoid MUTLIPLE_CONTENT_DISPOSITION error
                # in Chrome when the filename contains a comma.
                response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(filename)
            if encoding is not None:
                response['Content-Encoding'] = encoding
        elif not filename:
            # Get list of files w/urls.
            rv = {}
            filepath = event.datadir()
            fnames = []
            # Filter files for external users.
            if is_external(request.user):
                # XXX Note that the following snippet is repeated in views.py.
                # Construct the file list, filtering as necessary:
                for l in event.eventlog_set.all():
                    filename = l.filename
                    if len(filename):
                        version = l.file_version
                        tagnames = [t.name for t in l.tag_set.all()]
                        if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                            continue
                        if version>=0:
                            fnames.append(filename + ',' + str(version))
                        # We only want the unadorned filename once.
                        if filename not in fnames:
                            fnames.append(filename)
            else:
                for dirname, dirnames, filenames in os.walk(filepath):
                    dirname = dirname[len(filepath):]  # cut off base event dir path
                    for filename in filenames:
                        # relative path from root of event data dir
                        filename = os.path.join(dirname, filename)
                        fnames.append(filename)

            files = []
            for filename in fnames:
                rv[filename] = reverse("files", args=[graceid, filename], request=request)
                files.append({
                        'name' : filename,
                        'link' :  reverse("files",
                            args=[graceid, filename],
                            request=request),
                        })
            response = Response(rv)
        elif os.path.isdir(filepath):
            # XXX Really?
            response = HttpResponseForbidden("%s is a directory" % filename)
        else:
            response = HttpResponseServerError("Should not happen.")

        return response

    @event_and_auth_required
    def put(self, request, event, filename=""):
        """ File uploader.  Implements file versioning. """
        filename = filename or ""
        filepath = os.path.join(event.datadir(), filename)

        try:
            # Open / Write the file.
            fdest = VersionedFile(filepath, 'w')
            f = request.data['upload']
            for chunk in f.chunks(): 
                fdest.write(chunk)
            fdest.close()
            file_version = fdest.version

            rv = {}
            # XXX this seems wobbly.
            longname = fdest.name
            shortname = longname[longname.rfind(filename):]
            rv['permalink'] = reverse(
                    "files", args=[event.graceid(), shortname], request=request)
            response = Response(rv, status=status.HTTP_201_CREATED)
        except Exception, e:
            # XXX This needs some thought.
            response = Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            # XXX Uhm, we don't to try creating a log message for this, right?
            return response

        # Create a log entry to document the file upload. 
        logentry = EventLog(event=event,
                           issuer=request.user,
                           comment='',
                           filename=filename,
                           file_version=file_version)
        try:
            logentry.save()
        except:
            # XXX something should be done here.
            pass

        # If the user is external, we need to try to tag the log entry appropriately
        if is_external(request.user):
            try:
                tag = Tag.objects.get(name=settings.EXTERNAL_ACCESS_TAGNAME)
                tag.eventlogs.add(logentry)
            except:
                # XXX probably should at least log a warning here.
                pass

        try:
            description = "UPLOAD: {0}".format(filename)
            issueAlertForUpdate(event, description, doxmpp=True, 
                filename=filename, serialized_object = eventLogToDict(logentry))
        except:
            # XXX something should be done here.
            pass

        return response

class FileMeta(APIView):
    """File Metadata Resource"""
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    pass

class PerformanceInfo(APIView):
    """
    Serialized performance information
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (parsers.MultiPartParser,)

    def get(self, request, *args, **kwargs):
        user_groups = set(request.user.groups.all())
        allowed_groups = set([])
        try:
            allowed_groups = set([
                AuthGroup.objects.get(name=settings.LVC_GROUP),
                AuthGroup.objects.get(name=settings.EXEC_GROUP),
            ])
        except:
            pass

        if not user_groups & allowed_groups:
            return HttpResponseForbidden("Forbidden")

        try:
            performance_info = get_performance_info()
        except Exception, e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(performance_info,status=status.HTTP_200_OK)


#==================================================================
# VOEvent Resources

class VOEventList(APIView):
    """VOEvent List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        voeventset = event.voevent_set.order_by("created","N")
        count = voeventset.count()

        voevents = [ voeventToDict(voevent, request)
                for voevent in voeventset.iterator() ]

        rv = {
                'start': 0,
                'numRows' : count,
                'links' : {
                    'self' : request.build_absolute_uri(),
                    'first' : request.build_absolute_uri(),
                    'last' : request.build_absolute_uri(),
                    },
                'voevents' : voevents,
             }
        return Response(rv)

    @event_and_auth_required
    def post(self, request, event):
        voevent_type = request.data.get('voevent_type', None)
        if not voevent_type:
            msg = "You must provide a valid voevent_type."
            return Response({'error': msg}, status = status.HTTP_400_BAD_REQUEST)

        internal = request.data.get('internal', 1)
            
        skymap_type = request.data.get('skymap_type', None)
        skymap_filename = request.data.get('skymap_filename', None)
        skymap_image_filename = request.data.get('skymap_image_filename', None)

        if (skymap_filename and not skymap_type) or (skymap_type and not skymap_filename):
            msg = "Both or neither of skymap_time and skymap_filename must be specified."
            return Response({'error': msg}, status = status.HTTP_400_BAD_REQUEST)

        # Instantiate the voevent and save in order to get the serial number
        voevent = VOEvent(voevent_type=voevent_type, event=event, issuer=request.user)

        try:
            voevent.save()
        except Exception as e:
            return Response("Failed to create VOEvent: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Now, you need to actually build the VOEvent.
        try:
            voevent_text, ivorn = buildVOEvent(event, voevent.N, voevent_type, request,
                skymap_filename = skymap_filename, skymap_type = skymap_type,
                skymap_image_filename = skymap_image_filename, internal = internal)
        except VOEventBuilderException, e:
            msg = "Problem building VOEvent: %s" % str(e)
            return Response({'error': msg}, status = status.HTTP_400_BAD_REQUEST)

        voevent_display_type = dict(VOEvent.VOEVENT_TYPE_CHOICES)[voevent_type].capitalize()
        filename = "%s-%d-%s.xml" % (event.graceid(), voevent.N, voevent_display_type)
        filepath = os.path.join(event.datadir(), filename)
        fdest = VersionedFile(filepath, 'w')
        fdest.write(voevent_text)
        fdest.close()
        file_version = fdest.version

        voevent.filename = filename
        voevent.file_version = file_version
        voevent.ivorn = ivorn
        voevent.save()

        rv = voeventToDict(voevent, request=request)

        # Create LogEntry to document the new VOEvent.
        logentry = EventLog(event=event,
                             issuer=request.user,
                             comment='',
                             filename=filename,
                             file_version=file_version)
        try:
            logentry.save()
        except:
            rv['warnings'] = 'Problem saving log entry for VOEvent %s of %s' % (voevent.N, 
                event.graceid()) 

        # Tag log entry as 'sky_loc'
        tmp = EventLogTagDetail()
        retval = tmp.put(request, event.graceid(), logentry.N, 'em_follow') 
        # XXX This seems like a bizarre way of getting an error message out.
        if retval.status_code != 201:
            rv['tagWarning'] = 'Error tagging VOEvent log message as em_follow.'

        # Issue alert.
        description = "VOEVENT: %s" % filename
        issueAlertForUpdate(event, description, doxmpp=True, 
            filename=filename, serialized_object=rv)

        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        return response

class VOEventDetail(APIView):
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, n):
        try:
            voevent = event.voevent_set.filter(N=n)[0]
        except:
            return Response("VOEvent does not exist.",
                    status=status.HTTP_404_NOT_FOUND)
        return Response(voeventToDict(voevent, request=request))

#==================================================================
# OperatorSignoff 

class OperatorSignoffList(APIView):
    """Operator Signoff List Resource

    At present, this only supports GET
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        signoff_set = event.signoff_set.all()
        count = signoff_set.count()
        signoff = [ signoffToDict(s) for s in signoff_set.iterator() ]

        rv = {
                'start': 0,
                'numRows' : count,
                'links' : {
                    'self' : request.build_absolute_uri(),
                    'first' : request.build_absolute_uri(),
                    'last' : request.build_absolute_uri(),
                    },
                'signoff' : signoff,
             }
        return Response(rv)

