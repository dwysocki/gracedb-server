from __future__ import absolute_import
import json
import logging
import os
import shutil
try:
    from StringIO import StringIO
except ImportError:  # python >= 3
    from io import StringIO

from django.conf import settings
from django.contrib.auth.models import User, Permission, Group as DjangoGroup
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseForbidden, \
    HttpResponseNotFound, HttpResponseServerError, HttpResponseBadRequest
from django.http.request import QueryDict
from django.utils.functional import wraps
from django.utils.http import urlencode

# Stuff for the LigoLwRenderer (converted from glue to ligo.lw)
from ligo.lw import ligolw
# lsctables MUST be loaded before utils.
from ligo.lw import utils
from ligo.lw.utils import ligolw_add
from core.ligolw import ThoroughFlexibleContentHandler
from ligo.lw.lsctables import use_in

from guardian.models import GroupObjectPermission
from rest_framework import authentication, parsers, serializers, status
from rest_framework.exceptions import ValidationError as DrfValidationError
from rest_framework.permissions import IsAuthenticated, BasePermission, \
    SAFE_METHODS
from rest_framework.renderers import BaseRenderer, JSONRenderer, \
    BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts.issuers.events import EventAlertIssuer, EventLogAlertIssuer, \
    EventVOEventAlertIssuer, EventPermissionsAlertIssuer
from annotations.voevent_utils import construct_voevent_file
from api.throttling import BurstAnonRateThrottle
from core.http import check_and_serve_file
from core.vfile import create_versioned_file
from events.forms import CreateEventForm
from events.models import Event, Group, Search, Pipeline, EventLog, Tag, \
    Label, Labelling, EMGroup, EMBBEventLog, EMSPECTRUM, VOEvent, GrbEvent
from events.permission_utils import user_has_perm, filter_events_for_user, \
    is_external, check_external_file_access
from events.translator import handle_uploaded_data
from events.view_logic import create_label, get_performance_info, \
    delete_label, _createEventFromForm, create_eel, create_emobservation
from events.view_utils import eventToDict, eventLogToDict, labelToDict, \
    embbEventLogToDict, voeventToDict, emObservationToDict, signoffToDict, \
    skymapViewerEMObservationToDict, BadFARRange, check_query_far_range, \
    groupeventpermissionToDict
from search.forms import SimpleSearchForm
from search.query.events import parseQuery, ParseException
from superevents.models import Superevent
from .permissions import CanUpdateGrbEvent
from .throttling import EventCreationThrottle, AnnotationThrottle
from ..mixins import InheritDefaultPermissionsMixin
from ...utils import api_reverse

# Set up logger
logger = logging.getLogger(__name__)

# Set up content handler
use_in(ThoroughFlexibleContentHandler)

# For checking queries in the event that the user is external
REST_FRAMEWORK_SETTINGS = getattr(settings, 'REST_FRAMEWORK', {})
PAGINATE_BY = REST_FRAMEWORK_SETTINGS.get('PAGINATE_BY', 10)

# Custom APIView class for inheriting default permissions
class InheritPermissionsAPIView(InheritDefaultPermissionsMixin, APIView):
    pass


# A custom permission class for the EventDetail view. 
class IsAuthorizedForEvent(BasePermission):
    def has_object_permission(self, request, view, obj):
        # "Safe methods" only require view permission.
        if request.method in SAFE_METHODS:
            shortname = 'view'
        # "Unsafe methods" require change permissions on the event.
        # Note that DELETE is only implemented for event-log-tag 
        # relationships.
        elif request.method in ['PUT', 'PATCH', 'POST', 'DELETE']:
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
            group = DjangoGroup.objects.get(name=str(group_name))
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
#        graceid = obj.graceid
#        return dict([
#            (labelling.label.name,
#                reverse("labels",
#                    args=[graceid, labelling.label.name],
#                    request=request))
#            for labelling in obj.labelling_set.all()])
#
#    def get_links(self,obj):
#        request = self.context['request']
#        graceid = obj.graceid
#        return {
#            "neighbors" : reverse("neighbors", args=[graceid], request=request),
#            "log"   : reverse("eventlog-list", args=[graceid], request=request),
#            "files" : reverse("files", args=[graceid], request=request),
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
    # data is a dict
    if 'events' in data:
        eventDictList = data['events']
    else:
        # There is only one event.
        eventDictList = [data,]
    xmldoc = ligolw.Document()
    for e in eventDictList:
        fname = os.path.join(e.datadir, "coinc.xml")
        if not os.path.exists(fname):
            raise MissingCoinc
        elif not os.access(fname, os.R_OK):
            raise CoincAccess
        utils.load_filename(fname, xmldoc=xmldoc, contenthandler=ThoroughFlexibleContentHandler)
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
        if 'error' in data:
            return data['error']
        
        xmldoc = assembleLigoLw(data)
        # XXX Aaargh! Just give me the contents of the xml doc. Annoying.
        output = StringIO()
        xmldoc.write(output)
        return output.getvalue()

class TSVRenderer(BaseRenderer):
    media_type = 'text/tab-separated-values'
    format = 'tsv'

    def render(self, data, media_type=None, renderer_context=None):
        if 'error' in data:
            return data['error']

        accessFun = {
            "labels" : lambda e: \
                ",".join(list(e['labels'])),
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
        if 'events' in data:
            for e in data['events']:
                row = [ accessFun.get(column, lambda e: defaultAccess(e,column))(e) for column in columns ]
                outTable.append("\t".join(row))
        outTable = "\n".join(outTable)
       
        return outTable

#==================================================================
# Events

class EventList(InheritPermissionsAPIView):
    """
    This resource represents the collection of all candidate events in GraceDB.

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
    permission_classes = (IsAuthenticated,IsAuthorizedForPipeline)
    parser_classes = (parsers.MultiPartParser,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer, LigoLwRenderer, TSVRenderer,)
    throttle_classes = (BurstAnonRateThrottle, EventCreationThrottle,)

    def get(self, request, *args, **kwargs):

        """I am the GET docstring for EventList"""
        query = request.query_params.get("query")
        count = request.query_params.get("count", PAGINATE_BY)
        start = request.query_params.get("start", 0)
        sort = request.query_params.get("sort", "-created")
        columns = request.query_params.get("columns", "")


        events = Event.objects.filter(graceid__isnull=False)

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
                except ParseException: 
                    d = {'error': 'Invalid query' }
                    return Response(d,status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    d = {'error': str(e) }
                    return Response(d,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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

        last = max(0, (numRows // count)) * count
        rv = {}
        links = {}
        rv['links'] = links
        rv['events'] = [eventToDict(e, request=request)
                for e in events[start:start+count]]
        baseuri = api_reverse('events:event-list', request=request)

        links['self'] = request.build_absolute_uri()

        d = { 'start' : 0, "count": count, "sort": sort }
        if query: d['query'] = query
        links['first'] = baseuri + "?" + urlencode(d)

        d['start'] = last
        links['last'] = baseuri + "?" + urlencode(d)

        if start != last:
            d['start'] = start+count
            links['next'] = baseuri + "?" + urlencode(d)
        rv['numRows'] = numRows

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
        except Exception as e:
            try:
                status_code = e.status_code
            except:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({'error': str(e)}, status=status_code)

        return response

    #@pipeline_auth_required
    def post(self, request, format=None):
        rv = {}
        rv['warnings'] = []
        pipeline_name = request.data['pipeline']

        # AEP (May 2020): begin to depreciate pipelines that are no longer 
        # maintained or supported. Not sure this conditional is the best way
        # to do it, but it's a start.
        if pipeline_name not in settings.DEPRECIATED_PIPELINES:
            # Check user authorization for pipeline. 
            group_name = request.data.get('group', None) 
            if not group_name=='Test':
                try:
                    pipeline = Pipeline.objects.get(name=pipeline_name)
                except:
                    return Response({'error': "Please provide a valid pipeline."},
                        status = status.HTTP_400_BAD_REQUEST)
                if not user_has_perm(request.user, "populate", pipeline):
                    return HttpResponseForbidden("You don't have permission on this pipeline.")
    
                # Get search since we won't block MDC event submissions even if the
                # pipeline is disabled
                search_name = request.data.get('search', None)
                if not pipeline.enabled and search_name != 'MDC':
                    err_msg = ('The {0} pipeline has been temporarily disabled by '
                        'an EM advocate due to suspected misbehavior.').format(
                        pipeline.name)
                    return HttpResponseBadRequest(err_msg)
    
            # The following looks a bit funny but it is actually necessary. The 
            # django form expects a dict containing the POST data as the first
            # arg, and a dict containing the FILE data as the second. In the 
            # django-restframework, however, both are in request.data
    
            # TP (21 Nov 2017): Hack to allow basic event submission without
            # labels to function with versions of gracedb-client before 1.26.
            # Should be removed eventually.
            if (request.data.get('labels') == ''):
                request.data.pop('labels', None)
    
            form = CreateEventForm(request.data, request.data)
            if form.is_valid():
                event, warnings = _createEventFromForm(request, form)
                if event:
                    rv.update(eventToDict(event, request=request))
                    rv['warnings'] += warnings
                    response = Response(rv, status=status.HTTP_201_CREATED)
                    response["Location"] = api_reverse(
                            'events:event-detail',
                            args=[event.graceid],
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
        else:
            err_msg =("The %s pipeline is no longer supported in GraceDB. Please "
                    "contact an administrator to re-enable support." % pipeline_name)
            return HttpResponseBadRequest(err_msg)


class RawdataParser(parsers.BaseParser):
    media_type = 'application/octet-stream'

    def parse(self, stream, media_type=None, parser_context=None):
        class FakeFile():
            def __init__(self, name, read):
                self.name = name
                self.read = read
        files = { 'upload' : FakeFile("initial.data", stream.read) }
        data = {}
        return parsers.DataAndFiles(data, files)

class LigoLwParser(parsers.MultiPartParser):
    # XXX Revisit this.
    #  Doing it right involves refactoring translator.py
    media_type = "multipart/form-data"
    def parse(self, *args, **kwargs):
        data = parsers.MultiPartParser.parse(self, *args, **kwargs)
        return data

class EventDetail(InheritPermissionsAPIView):
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
        except Exception as e:
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
        except Exception as e:
            return Response(str(e))

        # Compile far and nscand for alerts
        old_far = event.far
        old_nscand = event.is_ns_candidate()

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

        # Create versioned file
        f = request.data['eventFile']
        version = create_versioned_file(f.name, event.datadir, f)

        # Extract Info from uploaded data
        uploadDestination = os.path.join(event.datadir, f.name)
        handle_uploaded_data(event, uploadDestination)
        event.submitter = request.user

        # Save event
        event.save()

        # Issue alert
        EventAlertIssuer(event, alert_type='update').issue_alerts(
            old_far=old_far, old_nscand=old_nscand)

        return Response(status=status.HTTP_202_ACCEPTED)


# New class *only* for updating GRB event properties
class GrbEventPatchView(InheritPermissionsAPIView):
    permission_classes = (IsAuthenticated, IsAuthorizedForEvent,
                          CanUpdateGrbEvent)
    updatable_attributes = ['t90', 'redshift', 'designation', 'ra', 'dec',
        'error_radius']

    def process_data(self, data):
        cleaned_data = {}
        for k, v in data.items():
            if k in ['t90', 'redshift', 'ra', 'dec', 'error_radius']:
                try:
                    cleaned_data[k] = float(v)
                except ValueError as e:
                    err_msg = "Parameter '{k}' must be a float".format(k=k)
                    raise DrfValidationError(err_msg)
            elif k == 'designation':
                try:
                    cleaned_data[k] = str(v)
                except ValueError as e:
                    err_msg = "Parameter '{k}' must be a string".format(k=k)
                    raise DrfValidationError(err_msg)
        return cleaned_data

    def get_attributes_to_update(self, grbevent, data):
        attrib_to_update = [k for k in data if (k in self.updatable_attributes
                            and getattr(grbevent, k, None) != data[k])]

        # If none, raise an error
        if not attrib_to_update:
            raise DrfValidationError('Request would not modify the GRB event')

        return {k: data[k] for k in attrib_to_update}

    def generate_log_message(self, grbevent, update_dict):
        # Templates
        comment = "Updated GRB event parameters: {msg}"
        param_template = "{name}: {old} -> {new}"

        # Message strings for updated parameters
        update_list = [
            param_template.format(
                name=k,
                old=getattr(grbevent, k),
                new=update_dict[k]
            )
            for k in update_dict
        ]
        return comment.format(msg=", ".join(update_list))

    @event_and_auth_required
    def patch(self, request, grbevent):
        # grbevent here should be a GrbEvent due to the way
        # event_and_auth_required works

        # Make sure this is a GRB event
        if (grbevent.pipeline.name not in settings.GRB_PIPELINES
            or not isinstance(grbevent, GrbEvent)):
            msg = ("Cannot update GRB event parameters for non-GRB event "
                   "{gid}").format(gid=grbevent.graceid)
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        # Process data - should be all floats except designation
        data = self.process_data(request.data)

        # Get attributes to update and their values
        update_dict = self.get_attributes_to_update(grbevent, data)

        # Generate log message before updating event
        update_message = self.generate_log_message(grbevent, update_dict)

        # Update the event
        for attribute in update_dict:
            setattr(grbevent, attribute, update_dict[attribute])
        grbevent.save()

        # Save log message
        grbevent.eventlog_set.create(comment=update_message,
                                     issuer=request.user)

        # Send LVAlert
        EventAlertIssuer(grbevent, alert_type='update').issue_alerts(
            old_far=grbevent.far, old_nscand=grbevent.is_ns_candidate())

        return Response(eventToDict(grbevent, request=request))


#==================================================================
# Neighbors

class EventNeighbors(InheritPermissionsAPIView):
    """The neighbors of an event.
    ### GET
    The `neighborhood` parameter lets you select a GPS time
    range for what it means to be a neighbor.  Can be of the
    form `neighborhood=N` or `neighborhood=N,M` to select
    neighbors in the (inclusive) GPS time range [x-N,x+N] or [x-N, x+M],
    where x is the GPS time of the event in question.
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    # XXX Since this returns an event list, we could add the LigoLW
    # and TSV renderers.
    @event_and_auth_required
    def get(self, request, event):
        if 'neighborhood' in request.query_params:
            delta = request.query_params['neighborhood']
            try:
                if delta.find(',') < 0:
                    neighborhood = (int(delta), int(delta))
                else:
                    neighborhood = list(map(int, delta.split(',')))
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
                    'event': api_reverse("events:event-detail",
                        args=[event.graceid], request=request),
                    }
                })

#==================================================================
# Labels

# XXX NOT FINISHED

class EventLabel(InheritPermissionsAPIView):
    """Event Label"""
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event, label=None):
        if label is not None:
            theLabel = event.labelling_set.filter(label__name=label).all()
            if len(theLabel) < 1:
                return Response("Label %s Not Found" % label,
                        status=status.HTTP_404_NOT_FOUND)
            theLabel = theLabel[0]
            return Response(labelToDict(theLabel, request=request))
        else:
            labels = [ labelToDict(x,request=request)
                    for x in event.labelling_set.all() ]
            return Response({
                'links' : [{
                    'self': request.build_absolute_uri(),
                    'event': api_reverse("events:event-detail",
                        args=[event.graceid],
                        request=request),
                    }],
                'labels': labels
                })

    @event_and_auth_required
    def put(self, request, event, label):
        try:
            rv, label_created = create_label(event, request, label)
        except (ValueError, Label.ProtectedLabelError) as e:
            return Response(str(e),
                        status=status.HTTP_400_BAD_REQUEST)

        # Return response and status code
        if label_created:
            return Response(rv, status=status.HTTP_201_CREATED)
        else:
            return Response(rv, status=status.HTTP_200_OK)

    @event_and_auth_required
    def delete(self, request, event, label):

        try:
            rv = delete_label(event, request, label)
        except Labelling.DoesNotExist as e:
            return Response(str(e), status=status.HTTP_404_NOT_FOUND)
        except (ValueError, Label.ProtectedLabelError) as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

#==================================================================
# EventLog

class EventLogList(InheritPermissionsAPIView):
    """Event Log List Resource

    POST param 'message'
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (BurstAnonRateThrottle, AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        logset = event.eventlog_set.order_by("created","N")

        # Filter log messages for external users.
        if is_external(request.user):
            logset = logset.filter(tags__name=settings.EXTERNAL_ACCESS_TAGNAME)

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
        message = request.data.get('comment')
        label = request.data.get('label', None)
        # Handle requests encoded as multipart/form or regular JSONs
        if isinstance(request.data, QueryDict):
            # request.data is a MultiValueDict
            tagnames = request.data.getlist('tagname', [])
            displayNames = request.data.getlist('displayName', [])
            #label = request.data.getlist('label', None)
        else:
            # request.data is a normal dict
            tagnames = request.data.get('tagname', [])
            displayNames = request.data.get('displayName', [])

        try:
            uploadedFile = request.data['upload'] 
            self.check_object_permissions(self.request, event)
        except:
            uploadedFile = None

        filename = ""
        file_version = None
        if uploadedFile:
            filename = uploadedFile.name 

            try:
                # Open / Write the file.
                file_version = create_versioned_file(filename, event.datadir,
                                                     uploadedFile)
            except Exception as e:
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

        # Check how to handle displayNames
        if len(displayNames) == len(tagnames):
            use_display_names = True
        else:
            use_display_names = False
            #https://stackoverflow.com/questions/52367379/why-is-django-rest-frameworks-request-data-sometimes-immutable
            try:
                request.data['displayName'] = ''
            except AttributeError:
                mutable = request.data._mutable # save state
                request.data._mutable = True    # make mutable
                request.data['displayName'] = ''
                request.data._mutable = mutable # return to original state

        tw_dict = {}
        if tagnames and len(tagnames):
            for i,tagname in enumerate(tagnames):
                n = logentry.N

                # Modify request data to include display name for this tag
                if use_display_names:
                    request.data['displayName'] = displayNames[i]

                tmp = EventLogTagDetail()
                retval = tmp.put(request, event.graceid, n, tagname) 
                # XXX This seems like a bizarre way of getting an error message out.
                if retval.status_code != 201:
                    return Response(('Log message created, but error creating '
                        'tag: {0}').format(retval.data),
                        status=retval.status_code)
                    #tw_dict = {'tagWarning': 'Error creating tag %s.' % tagname }
                    
        # Serialize the event log object *after* adding tags!
        rv = eventLogToDict(logentry, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        #if 'tagWarning' in tw_dict:
        #    response['tagWarning'] = tw_dict['tagWarning']

        # Issue alert.
        EventLogAlertIssuer(logentry, alert_type='log').issue_alerts()

        # Now apply labels
        if label:
            try:
                rv, label_created = create_label(event, request, label)
            except (ValueError, Label.ProtectedLabelError) as e:
                return Response(str(e),
                            status=status.HTTP_400_BAD_REQUEST)

        return response

class EventLogDetail(InheritPermissionsAPIView):
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog):
        # XXX Access control to log messages for external users.
        if is_external(request.user):
            tagnames = [t.name for t in eventlog.tags.all()]
            if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                msg = 'You do not have permission to view this log message.'
                return HttpResponseForbidden(msg)
        return Response(eventLogToDict(eventlog, request=request))


#==================================================================
# EMBBEventLog (EEL)

class EMBBEventLogList(InheritPermissionsAPIView):
    """EMBB Event Log List Resource

    POST param 'message'
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (BurstAnonRateThrottle, AnnotationThrottle,)

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
            # Alert is issued in this code
            eel = create_eel(request.data, event, request.user)
        except ValueError as e:
            return Response("%s" % str(e), status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response("Failed to save EMBB entry: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response("Problem creating EEL: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = embbEventLogToDict(eel, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']

        return response

class EMBBEventLogDetail(InheritPermissionsAPIView):
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

class EMObservationList(InheritPermissionsAPIView):
    """EMObservation Record List Resource

    POST param 'message'
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (BurstAnonRateThrottle, AnnotationThrottle,)

    @event_and_auth_required
    def get(self, request, event):
        emo_set = event.emobservation_set.order_by("created","N")
        count = emo_set.count()

        # XXX Note the following hack.
        # If this JSON information is requested for skymapViewer, use a different
        # representation for backwards compatibility.
        if 'skymapViewer' in request.query_params:
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
            # Create EMObservation - alert is issued inside this code
            emo = create_emobservation(request, event)
        except ValueError as e:
            return Response("%s" % str(e), status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response("Failed to save EMBB observation record: %s" % str(e),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response("Problem creating EMBB Observation: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = emObservationToDict(emo, request=request)
        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['self']
        return response

class EMObservationDetail(InheritPermissionsAPIView):
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
                            "self" : api_reverse("events:eventlogtag-detail",
                                             args=[event.graceid,n,tag.name],
                                             request=request)
                          }
        else:
            # Links to all log messages of the event with this tag.
            rv['links'] = {
                            "logs" : [api_reverse("events:eventlog-detail", 
                                              args=[event.graceid,log.N], 
                                              request=request) 
                                      for log in event.getLogsForTag(tag.name)],
                            "self" : api_reverse("events:eventtag-detail",
                                             args=[event.graceid,tag.name],
                                             request=request)
                          }
    else:
        # XXX Unclear what the tag detail resource should be at this level.
        # For now, return an empty list.
        pass
#         rv['links'] = {
#                         "events" : [reverse("event-detail", 
#                                             args=[event.graceid], 
#                                             request=request) 
#                                     for event in tag.getEvents()],
#                         "self"   : reverse("tag-detail",
#                                            args=[tag.name],
#                                            request=request)
#                       }
    return rv


# XXX Unclear what the tag detail resource should be.
# class TagDetail(InheritPermissionsAPIView):
#     """Tag Detail Resource
#     """
#     permission_classes = (IsAuthenticated,)
# 
#     def get(self, request, tagname):
#         try:
#             tag = Tag.objects.filter(name=tagname)[0]
#         except Tag.DoesNotExist:
#             return Response("Tag not found.",
#                     status=status.HTTP_404_NOT_FOUND)
#         return Response(tagToDict(tag,request=request))

class EventTagList(InheritPermissionsAPIView):
    """Event Tag List Resource
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    def get(self, request, event):
        # Return a list of links to all tags for this event.
        # XXX Technically, this list should be filtered based on whether the
        # user is external and has access to the logs. I don't think this is 
        # a big deal, though.
        rv = {
                'tags' : [
                    {
                        'self': api_reverse("events:eventtag-detail",
                            args=[event.graceid, tag.name], request=request),
                        'name': tag.name,
                        'displayName': tag.displayName
                    }
                for tag in event.getAvailableTags()
                ]
        }
        return Response(rv)

class EventTagDetail(InheritPermissionsAPIView):
    """Event Tag List Resource
    """
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

class EventLogTagList(InheritPermissionsAPIView):
    """Event Log Tag List Resource
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog):
        rv = {
                'tags' : [
                    {
                        'self': api_reverse("events:eventlogtag-detail",
                            args=[event.graceid, eventlog.N, tag.name],
                            request=request),
                        'name': tag.name,
                        'displayName': tag.displayName
                    }
                for tag in eventlog.tags.all()
                ]
        }

        return Response(rv)

class EventLogTagDetail(InheritPermissionsAPIView):
    """Event Log Tag Detail Resource
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)

    @event_and_auth_required
    @eventlog_required
    def get(self, request, event, eventlog, tagname):
        try:
            tag = eventlog.tags.filter(name=tagname)[0]
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
            tag = eventlog.tags.filter(name=tagname)[0]
            msg = "Log already has tag {0}".format(tag.name)
            return Response(msg,status=status.HTTP_409_CONFLICT)
        except:
            # Check authorization
            if is_external(request.user) and tagname == settings.EXTERNAL_ACCESS_TAGNAME:
                if eventlog.issuer != request.user:
                    msg = "You do not have permission to add or remove this tag."
                    return HttpResponseForbidden(msg)            

            # Look for the tag.  If it doesn't already exist, create it.
            #tag, created = Tag.objects.get_or_create(name=tagname)
            try:
                tag, created = Tag.objects.get_or_create(name=tagname)
            except ValidationError as e:
                return Response(e.__str__(),
                    status=status.HTTP_400_BAD_REQUEST)
            displayName = request.data.get('displayName')
            if created:
                tag.displayName = displayName
                tag.save()

            # Now add the log message to this tag.
            tag.event_logs.add(eventlog)

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
            tag = eventlog.tags.filter(name=tagname)[0]
            tag.event_logs.remove(eventlog)

            # Is the tag empty now?  If so we can delete it.
            if not tag.event_logs.all():
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

            return Response("Tag deleted.",status=status.HTTP_204_NO_CONTENT)
        except:
            return Response("Tag not found.",status=status.HTTP_404_NOT_FOUND)

#==================================================================
# Permission Resources

def getContentType(event):
    return ContentType.objects.get_for_model(event)

class EventPermissionList(InheritPermissionsAPIView):
    """Event Permission List Resource
    """
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
            out_dict[group.name] = api_reverse("events:groupeventpermission-list", 
                args=[event.graceid,group.name], request=request) 
        return Response(rv, status=status.HTTP_200_OK)            

class GroupEventPermissionList(InheritPermissionsAPIView):
    """Group Event Permission List Resource
    """
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

class GroupEventPermissionDetail(InheritPermissionsAPIView):
    """Group Event Permission List Resource
    """
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

        except Exception as e:
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
            # Issue alert
            EventPermissionsAlertIssuer(gop, alert_type='exposed') \
                .issue_alerts()
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
            # Issue alert
            EventPermissionsAlertIssuer(gop, alert_type='hidden') \
                .issue_alerts()

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
        except Exception as e:
            return Response("Problem deleting permission: %s" % str(e), 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        rv = {'message': 'Permission successfully deleted.'}
        return Response(rv, status=status.HTTP_200_OK)            


class Files(InheritPermissionsAPIView):
    """Files Resource"""

    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    #parser_classes = (RawdataParser,)
    parser_classes = (parsers.MultiPartParser,)

    @event_and_auth_required
    def get(self, request, event, filename=""):
        # Do not filename to be None.  That messes up later os.path.join
        filename = filename or ""
        graceid = event.graceid

        filepath = os.path.join(event.datadir, filename)

        # Check permissions for external users
        if filename and os.path.isdir(filepath):
            # XXX Really?
            response = HttpResponseForbidden("%s is a directory" % filename)
        elif filename:
            if is_external(request.user):
                if not check_external_file_access(event, filename):
                    msg = "You do not have permission to view this file."
                    return HttpResponseForbidden(msg)
            response = check_and_serve_file(request, filepath,
                ResponseClass=Response)
        elif not filename:
            # Get list of files w/urls.
            rv = {}
            filepath = event.datadir
            fnames = []
            # Filter files for external users.
            if is_external(request.user):
                # XXX Note that the following snippet is repeated in views.py.
                # Construct the file list, filtering as necessary:
                for l in event.eventlog_set.all():
                    filename = l.filename
                    if len(filename):
                        version = l.file_version
                        tagnames = [t.name for t in l.tags.all()]
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
                rv[filename] = api_reverse("events:files", args=[graceid, filename], request=request)
                files.append({
                        'name' : filename,
                        'link' :  api_reverse("events:files",
                            args=[graceid, filename],
                            request=request),
                        })
            response = Response(rv)
        else:
            response = HttpResponseServerError("Should not happen.")

        return response

    @event_and_auth_required
    def put(self, request, event, filename=""):
        """ File uploader.  Implements file versioning. """
        filename = filename or ""

        try:
            # Open / Write the file.
            f = request.data['upload']
            file_version = create_versioned_file(filename, event.datadir, f)

            rv = {}
            # XXX this seems wobbly.
            longname = os.path.join(event.datadir, filename)
            shortname = longname[longname.rfind(filename):]
            rv['permalink'] = api_reverse(
                    "events:files", args=[event.graceid, shortname], request=request)
            response = Response(rv, status=status.HTTP_201_CREATED)
        except Exception as e:
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
                tag.event_logs.add(logentry)
            except:
                # XXX probably should at least log a warning here.
                pass

        try:
            EventLogAlertIssuer(logentry, alert_type='log').issue_alerts()
        except:
            # XXX something should be done here.
            pass

        return response


#==================================================================
# VOEvent Resources

class VOEventList(InheritPermissionsAPIView):
    """VOEvent List Resource
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (BurstAnonRateThrottle, AnnotationThrottle,)

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
        # Get data from request
        voevent_type = request.data.get('voevent_type', None)
        internal = request.data.get('internal', 1)
        skymap_type = request.data.get('skymap_type', None)
        skymap_filename = request.data.get('skymap_filename', None)
        open_alert = request.data.get('open_alert', 0)
        hardware_inj = request.data.get('hardware_inj', 0)
        CoincComment = request.data.get('CoincComment', None)
        ProbHasNS = request.data.get('ProbHasNS', None)
        ProbHasRemnant = request.data.get('ProbHasRemnant', None)
        BNS = request.data.get('BNS', None)
        NSBH = request.data.get('NSBH', None)
        BBH = request.data.get('BBH', None)
        Terrestrial = request.data.get('Terrestrial', None)
        HasMassGap = request.data.get('HasMassGap', None)
        Significant = request.data.get('Significant', 0)
        # old parameter included to warn users:
        MassGap = request.data.get('MassGap', None)

        # Get RAVEN data
        ext_gcn = request.data.get('ext_gcn', None)
        ext_pipeline = request.data.get('ext_pipeline', None)
        ext_search = request.data.get('ext_search', None)
        time_coinc_far = request.data.get('time_coinc_far', None)
        space_coinc_far = request.data.get('space_coinc_far', None)
        combined_skymap_filename = request.data.get('combined_skymap_filename',
             None)
        delta_t = request.data.get('delta_t', None)
        raven_coinc = request.data.get('raven_coinc', None)

        # Get VOEvent types as a dict (key = short form, value = long form)
        VOEVENT_TYPE_DICT = dict(VOEvent.VOEVENT_TYPE_CHOICES)

        # Check data
        error = False
        if not voevent_type or voevent_type not in VOEVENT_TYPE_DICT:
            error = True
            msg = "You must provide a valid voevent_type."
        elif ((skymap_filename and not skymap_type) or
              (skymap_type and not skymap_filename)):
            error = True
            msg = ("Both or neither of skymap_type and skymap_filename must "
                   "be specified.")
        elif not event.gpstime:
            error = True
            msg = "Cannot build a VOEvent because event has no gpstime."
        elif not event.far:
            error = True
            msg = "Cannot build a VOEvent because event has no FAR."
        elif (voevent_type in ["IN", "UP"] or
              voevent_type == "PR" and skymap_filename is not None):
            if skymap_filename is None:
                error = True
                msg = "Skymap filename not provided."
            if skymap_type is None:
                error = True
                msg = "Skymap type must be provided."

            # Check if skymap file exists
            skymap_file_path = os.path.join(event.datadir, skymap_filename)
            if not os.path.exists(skymap_file_path):
                error = True
                msg = "Skymap file {fname} does not exist".format(
                    fname=skymap_filename)
        elif time_coinc_far or space_coinc_far:
            if not ext_gcn:
                error = True
                msg = "External GCN ID not provided"
            elif not ext_pipeline:
                error = True
                msg = "External Pipeline not provided"
            elif not ext_search:
                error = True
                msg = "External Search not provided"
        elif MassGap:
            error = True
            msg = "MassGap has been replaced by HasMassGap"
            
        # If there's an error, return a 400 response
        if error:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        # Instantiate the voevent and save in order to get the serial number
        voevent = VOEvent(event=event, issuer=request.user,
            voevent_type=voevent_type, skymap_type=skymap_type,
            skymap_filename=skymap_filename, internal=internal,
            hardware_inj=hardware_inj, coinc_comment=CoincComment,
            prob_has_ns=ProbHasNS, prob_has_remnant=ProbHasRemnant,
            prob_bns=BNS, prob_nsbh=NSBH, prob_bbh=BBH,
            prob_terrestrial=Terrestrial, prob_has_mass_gap=HasMassGap,
            significant=Significant)

        try:
            voevent.save()
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("Failed to create VOEvent: %s" % str(e),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Now, you need to actually build the VOEvent.
        voevent_text, ivorn = construct_voevent_file(event, voevent,
                                                     request=request)

        if VOEVENT_TYPE_DICT[voevent_type] == 'earlywarning':
            voevent_display_type = 'EarlyWarning'
        else:
            voevent_display_type = VOEVENT_TYPE_DICT[voevent_type].capitalize()

        filename = "%s-%d-%s.xml" % (event.graceid, voevent.N, voevent_display_type)
        file_version = create_versioned_file(filename, event.datadir,
                                             voevent_text)

        voevent.filename = filename
        voevent.file_version = file_version
        voevent.ivorn = ivorn
        voevent.save()

        rv = voeventToDict(voevent, request=request)

        # Create LogEntry to document the new VOEvent.
        logentry = EventLog(event=event,
                             issuer=request.user,
                             comment='New VOEvent',
                             filename=filename,
                             file_version=file_version)
        try:
            logentry.save()
        except Exception as e:
            rv['warnings'] = 'Problem saving log entry for VOEvent %s of %s' % (voevent.N, 
                event.graceid) 

        # Tag log entry as 'em_follow')
        tmp = EventLogTagDetail()
        retval = tmp.put(request, event.graceid, logentry.N, 'em_follow')
        # XXX This seems like a bizarre way of getting an error message out.
        if retval.status_code != 201:
            return Response(('VOEvent log message created, but error tagging '
                'message: {0}').format(retval.data), status=retval.status_code)
            #rv['tagWarning'] = 'Error tagging VOEvent log message as em_follow.'

        # Issue alert.
        EventVOEventAlertIssuer(voevent, alert_type='voevent').issue_alerts()

        response = Response(rv, status=status.HTTP_201_CREATED)
        response['Location'] = rv['links']['self']
        return response

class VOEventDetail(InheritPermissionsAPIView):
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

class OperatorSignoffList(InheritPermissionsAPIView):
    """Operator Signoff List Resource

    At present, this only supports GET
    """
    permission_classes = (IsAuthenticated,IsAuthorizedForEvent,)
    throttle_classes = (BurstAnonRateThrottle, AnnotationThrottle,)

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
                'signoffs' : signoff,
             }
        return Response(rv)

