
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest, Http404
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response

from models import Event, Group, EventLog, Label, Tag, Pipeline, Search, GrbEvent
from models import EMGroup, Signoff
from forms import CreateEventForm, EventSearchForm, SimpleSearchForm, SignoffForm

from django.contrib.auth.models import User, Permission
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from permission_utils import filter_events_for_user, user_has_perm
from permission_utils import internal_user_required, is_external
from guardian.models import GroupObjectPermission

from view_logic import _createEventFromForm
from view_logic import get_performance_info
from view_logic import get_lvem_perm_status
from view_logic import create_eel
from view_logic import create_emobservation
from view_logic import create_label
from view_utils import assembleLigoLw, get_file
from view_utils import flexigridResponse, jqgridResponse
from view_utils import get_recent_events_string

import os
from django.conf import settings

from buildVOEvent import buildVOEvent, VOEventBuilderException
from utils.vfile import VersionedFile

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

import json
from django.utils.functional import wraps

# 
# for checking queries in the evnet that the user is external
#
from view_utils import BadFARRange, check_query_far_range
from query import parseQuery, ParseException

#
# A wrapper for retrieving an event and replacing graceid 
# in the arg list with the event itself.  Also checks 
# whether the user is authorized for this event.
#
def event_and_auth_required(view):
    @wraps(view)
    def inner(request, graceid, *args, **kwargs):
        try:
            event = Event.getByGraceid(graceid) 
        except Event.DoesNotExist:
            return HttpResponseNotFound("Event not found.")

        # Check permissions. If the event is specified, 'GET'
        # maps to 'view', and unsafe methods map to 'CHANGE'
        if request.method=='GET':
            if not user_has_perm(request.user, 'view', event):
                return HttpResponseForbidden("Forbidden")
        elif request.method in ['POST', 'DELETE']:                
            if not user_has_perm(request.user, 'change', event):
                return HttpResponseForbidden("Forbidden")

        return view(request, event, *args, **kwargs)
    return inner

def index(request):
#   assert request.user
    context = {}

    signoff_authorized = False
    signoff_instrument = None
    # XXX Note that this may not be the best way to perform the authorization check.
    # In particular, this assumes that the user can only be a member of one group 
    # at a time. That should be the case, however, as the control room machines are 
    # physically well separated and should have different IPs.
    if request.user:
        for group in request.user.groups.all():
            if '_control_room' in group.name:
                signoff_authorized = True
                signoff_instrument = group.name[:2].upper()
                break

    context['signoff_authorized'] = signoff_authorized
    context['signoff_instrument'] = signoff_instrument

    if signoff_authorized:
        label_name = signoff_instrument + 'OPS'
        events = Event.objects.filter(labelling__label__name=label_name)
        context['signoff_graceids'] = [e.graceid() for e in events]

    recent_events = '' 
    if request.user and not is_external(request.user) and settings.SHOW_RECENT_EVENTS_ON_HOME:
        try:
            recent_events = get_recent_events_string(request)
        except Exception, e:
            pass
    context['recent_events'] = recent_events
    
    return render_to_response('gracedb/index.html', context,
            context_instance=RequestContext(request))

def navbar_only(request):
    return render_to_response('navbar_only.html', {}, context_instance=RequestContext(request))

# SP Info and Privacy pages are required for Federation with InCommon. 
def spinfo(request):
    return render_to_response('gracedb/spinfo.html', {}, context_instance=RequestContext(request))

def spprivacy(request):
    return render_to_response('gracedb/spprivacy.html', {}, context_instance=RequestContext(request))

def discovery(request):
    return render_to_response('discovery.html', {}, context_instance=RequestContext(request))

@event_and_auth_required
def voevent(request, event):
    # Default VOEvent type is 'preliminary'
    voevent_type=request.GET.get('voevent_type', 'preliminary')
    internal=request.GET.get('internal', 1)
    try:
        voevent = buildVOEvent(event, request, voevent_type=voevent_type, internal=internal)
    # Exceptions caused by user errors of some sort.
    except VOEventBuilderException, e:
        return HttpResponseBadRequest(str(e))
    # All other exceptions return 500.
    except Exception, e:
        return HttpResponseServerError(str(e))
         
    return HttpResponse(voevent, content_type="application/xml")

def create(request):
    d = _create(request)
    if isinstance(d, HttpResponse):
        return d
    else:
        return render_to_response('gracedb/create.html',
                    d,
                    context_instance=RequestContext(request))

def _create(request):
    assert request.user

    rv = {}

    if request.method == "GET":
        rv['form'] = CreateEventForm()
    else:
        # Check authorization to create.
        group_name = request.POST.get('group', None)
        if not group_name=='Test':
            try:
                pipeline = Pipeline.objects.get(name=request.POST['pipeline'])
            except:
                return HttpResponseBadRequest("No valid pipeline provided.")

            if not user_has_perm(request.user, "populate", pipeline):
                return HttpResponseForbidden("You do not have permission to submit events to this pipeline.")

        form = CreateEventForm(request.POST, request.FILES)
        if form.is_valid():
            event, warnings = _createEventFromForm(request, form)
            if not event:
                # problem creating event...  XXX need an error page for this.
                raise Exception("\n".join(warnings))
            return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
        else:
            rv['form'] = form
    return rv

@event_and_auth_required
def logentry(request, event, num=None):
    if request.method == "POST":
        # create a log entry
        elog = EventLog(event=event, issuer=request.user)
        elog.comment = request.POST.get('comment') or request.GET.get('comment')
        uploadedFile = request.FILES.get('uploadedFile', None) if request.FILES else None
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
                return HttpResponseServerError(str(e))

        elog.filename = filename
        elog.file_version = file_version

        try:
            elog.save()
        except Exception as e:
            # XXX I feel like this should be a 500 error.  
            return HttpResponse("ERROR: %s" % str(e))

        tagname = request.POST.get('tagname')
        if tagname:
            # Look for the tag.  If it doesn't already exist, create it.
            try:
                tag = Tag.objects.filter(name=tagname)[0]
            except:
                displayName = request.POST.get('displayName')
                tag = Tag(name=tagname, displayName=displayName)
                tag.save()

            tag.eventlogs.add(elog)
            # Create a log entry to document the tag creation.
            num = elog.N
            msg = "Tagged message %s: %s " % (num, tagname)
            tlog = EventLog(event=event,
                               issuer=request.user,
                               comment=msg)
            try:
                tlog.save()
            except Exception as e:
                # XXX Maybe this isn't a big deal.  It's more of a 
                # warning than an error.
                msg = "Failed to save log entry to document tag:  "
                msg = msg + str(e)
                msg = msg + "\n However, the log message itself was saved."
                return HttpResponse(msg)
         
        # XXX If the user is external, tag the message appropriately.
        if is_external(request.user):
            try:
                tag = Tag.objects.get(name=settings.EXTERNAL_ACCESS_TAGNAME)
            except:
                displayName = request.POST.get('displayName')
                tag = Tag(name=tagname, displayName=displayName)
                tag.save()
            # I'm putting this in a try/except in case the user has already
            # added the external access tagname somehow, and the following 
            # would result in an IntegrityError
            try:
                tag.eventlogs.add(elog)
            except:
                pass

    elif request.method == "GET":
        if not user_has_perm(request.user, 'view', event):
            return HttpResponseForbidden("Forbidden")
        try:
            elog = event.eventlog_set.filter(N=num)[0]
        except Exception, e:
            raise Http404
        
        # Check authorization for this log message
        if is_external(request.user):
            tagnames = [t.name for t in elog.tag_set.all()]
            if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                msg = "You do not have permission to view this log message."
                return HttpResponseForbidden(msg)
    else:
        return HttpResponseBadRequest

    if not request.is_ajax():
        return HttpResponseRedirect(reverse(view, args=[event.graceid()]))

    rv = {}
    rv['comment'] = elog.comment
    rv['issuer'] = elog.issuer.username
    rv['created'] = elog.created.isoformat()
    rv['comment'] = elog.comment
    if tagname:
        rv['tagname'] = tagname

    return HttpResponse(json.dumps(rv), content_type="application/json")

@event_and_auth_required
def neighbors(request, event, delta1, delta2=None):
    context = {}
    try:
        delta1 = long(delta1)

        if delta2 is None:
            delta2 = delta1
            delta1 = -delta1
        else:
            delta2 = long(delta2)

    except ValueError: pass
    except: pass

    # Check that all the neighbors in the queryset are viewable.
    neighbor_qs = filter_events_for_user(event.neighbors((delta1,delta2)),
                    request.user, 'view')

    context['nearby'] = [(e.gpstime - event.gpstime, e) for e in neighbor_qs]
    context['neighbor_delta'] = "[%+d,%+d]" % (delta1, delta2)
    return render_to_response(
        'gracedb/neighbors_frag.html',
        context,
        context_instance=RequestContext(request))

@event_and_auth_required
def view(request, event):
    context = {}
    context['object'] = event
    context['eventdesc'] = get_file(event, "event.log")
    context['userdesc'] = get_file(event, "user.log")
    context['nearby'] = [(e.gpstime - event.gpstime, e)
                            for e in filter_events_for_user(event.neighbors(), request.user, 'view')]
#    context['skyalert_authorized'] = skyalert_authorized(request)
#    context['groups'] = [g.name for g in EMGroup.objects.all()]
    context['groups'] = [g.name for g in EMGroup.objects.order_by('name')]
    context['blessed_tags'] = settings.BLESSED_TAGS
    context['single_inspiral_events'] = list(event.singleinspiral_set.all())
    context['neighbor_delta'] = "[%+d,%+d]" % (-5,5)
    context['SKYMAP_VIEWER_SERVICE_URL'] = settings.SKYMAP_VIEWER_SERVICE_URL
    context['BOWER_URL'] = settings.BOWER_URL

    # XXX This is something of a hack. In the future, we will want to show the
    # executive user a list of groups and a two column list of radio buttons, showing
    # whether the group has access to this event or not, along with a submit button
    # at the bottom to commit changes. But for ER6, we won't need all that structure.
    can_expose_to_lvem, can_protect_from_lvem = get_lvem_perm_status(request,event)
    context['can_expose_to_lvem'] = can_expose_to_lvem
    context['can_protect_from_lvem'] = can_protect_from_lvem
    # Notice that the observers group is used here. This determines which group is 
    # given permission to access an event. We want it to be the observers group.
    context['lvem_group_name'] = settings.LVEM_OBSERVERS_GROUP

    if event.pipeline.name in settings.GRB_PIPELINES:
        context['can_modify_t90'] = request.user.has_perm('gracedb.t90_grbevent')

    # Is the user an external user? (I.e., not part of the LVC?) The template 
    # needs to know that in order to decide what pieces of information to show.
    context['user_is_external'] = is_external(request.user)

    # FAR must be floored in the same way as in the VOEvent.
    far_is_upper_limit = False
    display_far = event.far
    if event.far and is_external(request.user):
        if event.far < settings.VOEVENT_FAR_FLOOR:
            display_far = settings.VOEVENT_FAR_FLOOR
            far_is_upper_limit = True
    context['display_far'] = display_far
    context['far_is_upper_limit'] = far_is_upper_limit

    # Does the user have permission to sign off on the event as the control room operator?
    operator_signoff_authorized = False
    # XXX Note that this may not be the best way to perform the authorization check.
    # In particular, this assumes that the user can only be a member of one group 
    # at a time. That should be the case, however, as the control room machines are 
    # physically well separated and should have different IPs.
    for group in request.user.groups.all():
        if '_control_room' in group.name:
            operator_signoff_authorized = True
            context['signoff_instrument'] = group.name[:2].upper()
            context['signoff_form'] = SignoffForm()
            instrument = group.name[:2].upper()
            try:
                context['operator_signoff_object'] = Signoff.objects.get(event=event, 
                    instrument=instrument, signoff_type='OP')
            except:
                context['operator_signoff_object'] = None
            req_label = instrument + 'OPS'
            label_exists = req_label in [l.label.name for l in event.labelling_set.all()]

            context['operator_signoff_active'] = label_exists or context['operator_signoff_object']

            break
    context['operator_signoff_authorized'] = operator_signoff_authorized

    # XXX A lot of repetition here. Hopefully this will be fixed later.
    # Does the user have permission to sign off on the event as an EM advocate?
    advocate_signoff_authorized = False
    for group in request.user.groups.all():
        if settings.EM_ADVOCATE_GROUP==group.name:
            advocate_signoff_authorized = True
            context['signoff_form'] = SignoffForm()
            instrument = ''
            try:
                context['advocate_signoff_object'] = Signoff.objects.get(event=event, 
                    instrument=instrument, signoff_type='ADV')
            except:
                context['advocate_signoff_object'] = None
            req_label = 'ADVREQ'
            label_exists = req_label in [l.label.name for l in event.labelling_set.all()]

            context['advocate_signoff_active'] = label_exists or context['advocate_signoff_object']

            break
    context['advocate_signoff_authorized'] = advocate_signoff_authorized

    # Choose your template according to the event's pipeline.
    templates = ['gracedb/event_detail.html',]
    if event.pipeline.name in settings.COINC_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_coinc.html')
    elif event.pipeline.name in settings.GRB_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_GRB.html')
    elif event.pipeline.name.startswith('CWB'):
        templates.insert(0, 'gracedb/event_detail_CWB.html')
    elif event.pipeline.name in ['HardwareInjection',]:
        templates.insert(0, 'gracedb/event_detail_injection.html')
    elif event.pipeline.name in ['LIB',]:
        templates.insert(0, 'gracedb/event_detail_LIB.html')

    return render_to_response(templates, context, context_instance=RequestContext(request))

def search(request, format=""):
    if not request.user or not request.user.is_authenticated():
        return HttpResponseForbidden("Forbidden")
    # XXX DO NOT HARDCODE THIS
    # Also, user should be notified if their result hits this limit.
    limit = MAX_QUERY_RESULTS
    form2 = None

    if request.method == "GET" and "query" not in request.GET:
        form = SimpleSearchForm()
        form2 = EventSearchForm()
    else:
        if request.method == "POST" and 'query' not in request.POST:
            return oldsearch(request)
        if request.method == "GET":
            form = SimpleSearchForm(request.GET)
            rawquery = request.GET['query']
        else:
            form = SimpleSearchForm(request.POST)
            rawquery = request.POST['query']

        # If the user is external, we must check to make sure that any query on FAR
        # value is within the safe range.
        if is_external(request.user):
            try:
                check_query_far_range(parseQuery(rawquery))
            except BadFARRange:
                msg = 'FAR query out of range, upper limit must be below %s' % settings.VOEVENT_FAR_FLOOR
                return HttpResponseBadRequest(msg) 
            except ParseException:
                # If the user's query throws a parse exception, it is safe to 
                # proceed and show the error message in the search results template (red star)
                pass
            except Exception, e:
                return HttpResponseServerError(str(e))
        if form.is_valid():
            objects = form.cleaned_data['query']
            get_neighbors = form.cleaned_data['get_neighbors']

            # Filter objects according to user permissions.
            # NOTE: This is bad. Creates a complete list of pks to which the user has 
            # access for a given content type.  Then filters according to this list.
            #objects = guardian.shortcuts.get_objects_for_user(request.user, 'gracedb.view_event', objects)

            # Instead, use the alternative that uses perm info residing on the event itself.
            objects = filter_events_for_user(objects, request.user, 'view')

            if format == "json":
                return HttpResponse("Not Implemented")
            elif format == "flex":
                # Flexigrid request.
                return flexigridResponse(request, objects)
            elif format == "jqgrid":
                return jqgridResponse(request, objects)
            elif 'ligolw' in request.POST or 'ligolw' in request.GET:

                from glue.ligolw import utils
                if objects.count() > 1000:
                    # XXX  Make this -- Better.
                    return HttpResponse("Sorry -- no more than 1000 events currently allowed.")

                try:
                    xmldoc = assembleLigoLw(objects)
                except IOError:
                    msg = "At least one of the query results has no associated coinc.xml file."
                    msg += " LigoLw tables are available for queries that return only coinc inspiral events."
                    msg += " Please try your query again."
                    return HttpResponseBadRequest(msg)
                except Exception, e:
                    msg = "An error occured while trying to compile LigoLw results: %s" % str(e)
                    return HttpResponseServerError(msg)

                response = HttpResponse(content_type='application/xml')
                response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
                utils.write_fileobj(xmldoc, response)
                return response

            else:
                # XXX FIXME Use this instead.
                # count = objects.count()
                if objects.count() == 1:
                    title = "Query Results. %s event" % objects.count()
                else:
                    title = "Query Results. %s events" % objects.count()

                context = {
                            'title'         : title,
                            'form'          : form,
                            'formAction'    : reverse(search),
                            'maxCount'      : limit,
                            'rawquery'      : rawquery,
                            'get_neighbors' : get_neighbors,
                }
                return render_to_response('gracedb/event_list.html',
                    context, context_instance=RequestContext(request))

    return render_to_response('gracedb/query.html',
            { 'form' : form,
              'form2' : form2,
            },
            context_instance=RequestContext(request))

def oldsearch(request):
    assert request.user
    if request.method == 'GET':
        form = EventSearchForm()
    else:
        form = EventSearchForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['graceidStart']
            end = form.cleaned_data['graceidEnd']
            submitter = form.cleaned_data['submitter']
            groupname = form.cleaned_data['group']
            pipelinename = form.cleaned_data['pipeline']
            searchname = form.cleaned_data['search']
            labels = form.cleaned_data['labels']
            gpsStart =  form.cleaned_data['gpsStart']
            gpsEnd =  form.cleaned_data['gpsEnd']
            get_neighbors = form.cleaned_data['get_neighbors']

            textQuery = []

            if not groupname:
                # don't show test events unless explicitly requested
                # Scales?  Or should we find test group and do group= ?
                objects = Event.objects.exclude(group__name='Test')
            else:
                objects = Event.objects.all()

            # XXX Note, the uid field doesn't exist anymore. I'm not sure why this
            # stuff is in here. (Branson)
#            if start:
#                if start[0] != 'G':
#                    # XXX This is the deprecated uid stuff. Take it out when uid is gone.
#                    objects = objects.filter(uid__gte=start)
#                    objects = objects.filter(uid__startswith="0")
#                else:
#                    objects = objects.filter(id__gte=int(start[1:]))
#                    objects = objects.filter(uid="")
#            if end:
#                if end[0] != 'G':
#                    # XXX This is the deprecated uid stuff. Take it out when uid is gone.
#                    objects = objects.filter(uid__lte=end)
#                    objects = objects.filter(uid__startswith="0")
#                else:
#                    objects = objects.filter(id__lte=int(end[1:]))
#                    objects = objects.filter(uid="")

            if start:
                if start[0] in 'GEHMT':
                    objects = objects.filter(id__gte=int(start[1:]))
                else:
                    return HttpResponseBadRequest("Invalid GraceID")
            if end:
                if end[0] in 'GEHMT':
                    objects = objects.filter(id__lte=int(end[1:]))
                else:
                    return HttpResponseBadRequest("Invalid GraceID")

            if start and end:
                textQuery.append("gid: %s..%s" % (start, end))
            elif start or end:
                textQuery.append("gid: %s" % (start or end))

            if gpsStart != None or gpsEnd != None :
                if gpsStart == gpsEnd:
                    objects = objects.filter(gpstime=gpsStart)
                    textQuery.append("gpstime: %s" % gpsStart)
                else:
                    if gpsStart != None:
                        objects = objects.filter(gpstime__gte=gpsStart)
                    if gpsEnd != None:
                        objects = objects.filter(gpstime__lte=gpsEnd)
                    if gpsStart and gpsEnd:
                        textQuery.append("gpstime: %s .. %s" % (gpsStart, gpsEnd))
                    elif gpsStart:
                        textQuery.append("gpstime: %s..2000000000" % gpsStart)
                    else:
                        textQuery.append("gpstime: 0..%s" % gpsEnd)

            if submitter:
                try:
                    submitter_name = User.objects.get(id=submitter)
                except User.DoesNotExist:
                    submitter_name = "Error looking up user"
                objects = objects.filter(submitter=submitter)
                textQuery.append('submitter: "%s"' % submitter_name)
            if groupname:
                group = Group.objects.filter(name=groupname)[0]
                objects = objects.filter(group=group)
                textQuery.append("group: %s" % group.name)
            if pipelinename:
                pipeline = Pipeline.objects.get(name=pipelinename)
                objects = objects.filter(pipeline=pipeline)
                textQuery.append("pipeline: %s" % pipeline.name)
            if searchname:
                search = Search.objects.get(name=searchname)
                objects = objects.filter(search=search)
                textQuery.append("search: %s" % search.name)

            if labels:
                objects = objects.filter(labels__in=labels)
                textQuery.append("label: %s" % " ".join([
                    Label.objects.filter(id=l)[0].name for l in labels]))

            # Need this because events with multiple labels can appear multiple times!
            objects = objects.distinct()

            # Filter for user.
            objects = filter_events_for_user(objects, request.user, 'view')

            if objects.count() == 1:
                title = "Query Results. %s event" % objects.count()
            else:
                title = "Query Results. %s events" % objects.count()

            textQuery = " ".join(textQuery)
            simple_form = SimpleSearchForm({'query': textQuery})
            context = {
                'title'         : title,
                'form'          : simple_form,
                'maxCount'      : MAX_QUERY_RESULTS,
                'rawquery'      : textQuery,
                'get_neighbors' : get_neighbors,
            }
            return render_to_response('gracedb/event_list.html',
                context, context_instance=RequestContext(request))


    return render_to_response('gracedb/query.html',
            { 'form' : form },
            context_instance=RequestContext(request))

def latest(request):
    if not request.user or not request.user.is_authenticated():
        return HttpResponseForbidden("Forbidden")
    context = {}

    if request.method == "GET":
        form = SimpleSearchForm(request.GET)
    else:
        form = SimpleSearchForm(request.POST)

    template = 'gracedb/latest.html'
    context['form'] = form
    rawquery = request.GET.get('query') or request.POST.get('query') or ""
    context['rawquery'] = rawquery

    # If the user is external, we must check to make sure that any query on FAR
    # value is within the safe range.
    if is_external(request.user):
        try:
            check_query_far_range(parseQuery(rawquery))
        except BadFARRange:
            msg = 'FAR query out of range, upper limit must be below %s' % settings.VOEVENT_FAR_FLOOR
            return HttpResponseBadRequest(msg) 

    if form.is_valid():
        # XXX This makes the requests much faster for internal users.
        if is_external(request.user):
            objects = form.cleaned_data['query']
            objects = filter_events_for_user(objects, request.user, 'view')[0:50]
        else:
            objects = form.cleaned_data['query'][:50]
        context['objects'] = objects
        context['error'] = False
    else:
        context['error'] = True

    context['far_floor']        = settings.VOEVENT_FAR_FLOOR
    context['user_is_external'] = is_external(request.user)

    return render_to_response(
            template,
            context,
            context_instance=RequestContext(request))

#-----------------------------------------------------------------------------------
# For tags.  A new view function.  We need this because the API one would want users
# to have certs stored in their browser.
# XXX Get rid of this and use apiweb views instead?
#-----------------------------------------------------------------------------------

@event_and_auth_required
def taglogentry(request, event, num, tagname):
    eventlog = event.eventlog_set.filter(N=num)[0]

    if request.method == "POST":
        try:
            # Has this tag-eventlog relationship already been created? 
            tag = eventlog.tag_set.filter(name=tagname)[0]
            msg = "Log already has tag %s" % tagname
            return HttpResponse(msg, content_type="text")
        except:
            # Check authorization
            if is_external(request.user) and tagname == settings.EXTERNAL_ACCESS_TAGNAME:
                if request.user != eventlog.issuer:
                    msg = "You do not have permission to add or remove this tag."
                    return HttpResponseForbidden(msg)

            # Look for the tag.  If it doesn't already exist, create it.
            try:
                tag = Tag.objects.filter(name=tagname)[0]
            except:
                displayName = request.POST['displayName']
                tag = Tag(name=tagname, displayName=displayName)
                tag.save()

            # Now add the log message to this tag.
            tag.eventlogs.add(eventlog)

            # Create a log entry to document the tag creation.
            msg = "Tagged message %s: %s " % (num, tagname)
            logentry = EventLog(event=event,
                               issuer=request.user,
                               comment=msg)
            try:
                logentry.save()
            except Exception as e:
                msg = "Failed to save log entry documenting tag:  "
                msg = msg + str(e) + '\n'
                msg = "The tag itself, however, is saved."
                return HttpResponse(msg, content_type="text")
    elif request.method == "DELETE":
        try:
            # Has this tag-eventlog relationship already been created? 
            tag = eventlog.tag_set.filter(name=tagname)[0]
            tag.eventlogs.remove(eventlog)
        except:
            msg = "Attempted to delete tag that doesn't exist."
            return HttpResponseBadRequest(msg)

        # Check authorization
        if is_external(request.user) and tagname == settings.EXTERNAL_ACCESS_TAGNAME:
            if request.user != eventlog.issuer:
                msg = "You do not have permission to add or remove this tag."
                return HttpResponseForbidden(msg)

        # Create a log entry to document the tag deletion.
        msg = "Removed tag %s for message %s. " % (tagname, num)
        logentry = EventLog(event=event,
                           issuer=request.user,
                           comment=msg)
        try:
            logentry.save()
        except Exception as e:
            # Since the tag creation was successful, we'll return 200.
            return HttpResponse("Tag removed, but failed to create log entry: %s" % str(e),
                        content_type="text")

        return HttpResponse(msg, content_type="text")
    else:
        return HttpResponseBadRequest

    # Hopefully, this will only ever be called form inside a script.  Just in case...
    if not request.is_ajax():
        return HttpResponseRedirect(reverse(view, args=[event.graceid()]))

    # no need for a JSON response. 
    msg = "Successfully applied tag %s to log message %s." % (tagname, num)
    return HttpResponse(msg, content_type="text")

# Performance metrics.
@internal_user_required
def performance(request):

    try:
        context = get_performance_info()
    except Exception, e:
        return HttpResponseServerError(str(e))

    return render_to_response(
            'gracedb/performance.html',
            context,
            context_instance=RequestContext(request))

#
# A view for the list of files associated with an event.
# The idea is to get rid of that horrible /gracedb-files/ url.
#
@event_and_auth_required
def file_list(request, event):
    f = []
    if is_external(request.user):
        # Construct the file list, filtering as necessary:
        for l in event.eventlog_set.all():
            filename = l.filename
            if len(filename):
                version = l.file_version
                tagnames = [t.name for t in l.tag_set.all()]
                if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                    continue
                if version>=0:
                    f.append(filename + ',' + str(version))
                # We only want the unadorned filename once.
                if filename not in f:
                    f.append(filename)
    else:
        for dirname, dirnames, filenames in os.walk(event.datadir()):
            f.extend(filenames)
            break

    context = {}
    context['file_list'] = f
    context['title'] = 'Files for %s' % event.graceid() 
    context['graceid'] = event.graceid() 
        
    return render_to_response(
        'gracedb/event_filelist.html',
        context,
        context_instance=RequestContext(request)) 

#
# A view to modify the GroupObjectPermissions for an event.
# This is very non-RESTful. If the action is 'expose', you
# give the group both view and change permissions on the event.
# (Change perms allow annotation--like creating EELs or 
# log messages.) If the action is 'protect', both of these
# permissions are removed for the group in question.
#

def update_event_perms_for_group(event, group, action):
    # Get the content type out
    model_name = event.__class__.__name__.lower()
    ctype = ContentType.objects.get(app_label='gracedb', model=model_name)

    # Get the two relevant permissions.
    view = Permission.objects.get(codename='view_%s' % model_name)
    change = Permission.objects.get(codename='change_%s' % model_name)

    # Decide what to do
    if action=='expose':
        # Create two group object permissions
        GroupObjectPermission.objects.get_or_create(
            content_type=ctype, group=group, permission=view,
            object_pk=event.id)
        GroupObjectPermission.objects.get_or_create(
            content_type=ctype, group=group, permission=change,
            object_pk=event.id)
    elif action=='protect':
        # Retrieve both group object permissions
        # Delete them
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=ctype, group=group, permission=change,
                object_pk=event.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=ctype, group=group, permission=view,
                object_pk=event.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass

    # lastly 
    event.refresh_perms()

@event_and_auth_required
def modify_permissions(request, event):
    # Get group_name and action from POST
    if not request.method=='POST':
        msg = 'Modify_permissions only allows POST.'
        return HttpResponseBadRequest(msg)

    group_name = request.POST.get('group_name', None)
    action     = request.POST.get('action', None)

    if not group_name or not action:
        msg = 'Modify_permissons requires both group_name and action in POST.'
        return HttpResponseBadRequest(msg)

    # Make sure the user is authorized.
    if action=='expose':
        if not request.user.has_perm('guardian.add_groupobjectpermission'):
            msg = "You aren't authorized to create permission objects."
            return HttpResponseForbidden(msg)
    elif action=='protect':
        if not request.user.has_perm('guardian.delete_groupobjectpermission'):
            msg = "You aren't authorized to delete permission objects."
            return HttpResponseForbidden(msg)
    else:
        msg = "Unknown action. Choices are 'expose' and 'protect'."
        return HttpResponseBadRequest(msg)

    # Get the group
    try:
        g = AuthGroup.objects.get(name=group_name)
    except Group.DoesNotExist:
        return HttpResponseNotFound('Group not found')

    update_event_perms_for_group(event, g, action)

    # In case this is a subclass, let's check and assign default
    # perms on the underlying Event as well.
    if not type(event) is Event:
        underlying_event = Event.objects.get(id=event.id)
        update_event_perms_for_group(underlying_event, g, action)

    # Finished. Redirect back to the event.
    return HttpResponseRedirect(reverse("view", args=[event.graceid()]))

# A view to create embb log entries
@event_and_auth_required
def embblogentry(request, event, num=None):
    if request.method == "POST":
        try:
            create_eel(request.POST, event, request.user)
        except ValueError, e:
            return HttpResponseBadRequest(str(e))
        except Exception, e:
            return HttpResponseServerError(str(e))

        return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
    else:
        return HttpResponseBadRequest("This URL only supports POST.")

#        if not user_has_perm(request.user, 'view', event):
#              return HttpResponseForbidden("Forbidden")
#        if not num:
#            eels = event.embbeventlog_set.all()
#            ceels = []
#            for eel in eels:
#                color = md5(eel.group.name).hexdigest()[:6]
#                ceels.append([color, eel])
#            context = {"ceels":ceels}
#            return render_to_response('gracedb/embb.json', context, 
#                context_instance=RequestContext(request), mimetype="application/json")
#        else:
#            return HttpResponse(content="Individual EEL view in web interface not implemented.", 
#                status=501)
#            try:
#                eel = event.embbeventlog_set.filter(N=num)[0]
#            except Exception:
#                raise Http404
#    if not request.is_ajax():
#            context = {"eel":eel}
#            return render_to_response('gracedb/eel_detail.html', context, context_instance=RequestContext(request))

#        return HttpResponseRedirect(reverse(view, args=[graceid]))
#    rv = {}
#    rv['comment'] = eel.comment
#    rv['submitter'] = eel.issuer.username
#    rv['created'] = eel.created.isoformat()
#    return HttpResponse(json.dumps(rv), content_type="application/json")

# A view to create embb log entries
@event_and_auth_required
def emobservation_entry(request, event, num=None):
    if request.method == "POST":
        try:
            create_emobservation(request, event)
        except ValueError, e:
            return HttpResponseBadRequest(str(e))
        except Exception, e:
            return HttpResponseServerError(str(e))

        return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
    else:
        return HttpResponseBadRequest("This URL only supports POST.")

#
# Despite the name, this view function will handle updates to all of the 
# hand-entered GRB data, including t90, redshift, and event designation.
#
@event_and_auth_required
def modify_t90(request, event):
    if not request.method=='POST':
        msg = 'This URL only allows POST.'
        return HttpResponseBadRequest(msg)
    if not isinstance(event, GrbEvent):
        msg = 'This method only works on GrbEvent objects.'
        return HttpResponseBadRequest(msg)
    if not request.user.has_perm('gracedb.t90_grbevent'):
        msg = "You aren't authorized to modify GRB attributes."
        return HttpResponseForbidden(msg)

    designation = request.POST.get('designation', None)
    redshift    = request.POST.get('redshift', None)
    t90         = request.POST.get('t90', None)

    if not (t90 or designation or redshift):
        msg = 'This method requires one of: designation, redshift, or t90 in POST.'
        return HttpResponseBadRequest(msg)

    if t90:
        event.t90 = t90
    elif redshift:
        event.redshift = redshift
    elif designation:
        event.designation = designation
    event.save()
    
    # Finished. Redirect back to the event.
    return HttpResponseRedirect(reverse("view", args=[event.graceid()]))

# XXX So this should probably be moved into view_logic anyway.
from alert import issueXMPPAlert
from view_utils import signoffToDict
from models import SIGNOFF_TYPE_CHOICES

def get_signoff_type(stype):
    for t in SIGNOFF_TYPE_CHOICES:
        if stype in t:
            return t[0]
    return None

@event_and_auth_required
def modify_signoff(request, event):
    if not request.method=='POST':
        msg = 'create_operator_signoff only allows POST.'
        return HttpResponseBadRequest(msg)
    authorized = False
    instrument = ''
    action = request.POST.get('action', 'create')
    signoff_type = request.POST.get('signoff_type', 'operator')

    if signoff_type=='operator':
        # XXX Note that this may not be the best way to perform the authorization check.
        # In particular, this assumes that the user can only be a member of one group 
        # at a time. That should be the case, however, as the control room machines are 
        # physically well separated and should have different IPs.
        for group in request.user.groups.all():
            if '_control_room' in group.name:
                authorized = True
                instrument = group.name[:2].upper()
                break
        if not len(instrument):
            msg = "Unknown instrument/control room for signoff."
            return HttpResponseBadRequest(msg)

        req_label = instrument + 'OPS'
        label_stem = instrument
    elif signoff_type=='advocate':
        user_groups = [g.name for g in request.user.groups.all()]
        if settings.EM_ADVOCATE_GROUP in user_groups:
            authorized = True

        req_label = 'ADVREQ'
        label_stem = 'ADV'
    else:
        msg = 'Unknown signoff type.'
        return HttpResponseBadRequest(msg)

    if not authorized:
        msg += "You are not authorized to perform the requested action."
        return HttpResponseForbidden(msg)      

    existing = Signoff.objects.filter(event=event, instrument=instrument, 
        signoff_type=get_signoff_type(signoff_type))
    if existing.count() and action=='create':
        msg = 'Cannot create multiple signoffs for the same event.'
        return HttpResponseBadRequest(msg) 

    f = SignoffForm(request.POST)
    status = None
    comment = None
    if f.is_valid():
        status = f.cleaned_data['status']
        comment = f.cleaned_data['comment']

    if action=='create':
        if status==None:
            msg = "Please select a valid status."
            return HttpResponseBadRequest(msg)

        # Create the OperatorSignoff object.
        signoff = Signoff.objects.create(submitter = request.user,
            event = event, instrument = instrument, 
            status = status, comment = comment,
            signoff_type = get_signoff_type(signoff_type))

        # Remove the request label.
        for l in event.labelling_set.all():
            if l.label.name == req_label:
                l.delete()

        # Create a new label.
        label_name = label_stem + status
        create_label(event, request, label_name, doAlert=False, doXMPP=False)

        # Create a log message
        msg = "%s signoff certified status as %s" % (signoff_type, status)
        if len(instrument):
            msg += ' for %s' % instrument        
        if comment:
            msg += ': %s' % comment
        logentry = EventLog.objects.create(event=event, issuer=request.user, comment=msg)

        # XXX Ugh. Hardcoding tagname here.
        # Add a tag to the log message
        try:
            tag = Tag.objects.get(name='em_follow')
            tag.eventlogs.add(logentry)
        except:
            pass

        # Issue an alert.
        issueXMPPAlert(event, location='', alert_type="signoff", description=status, 
            serialized_object = signoffToDict(signoff))

    elif action=='edit':
        # get the existing object
        signoff = None
        if existing.count()==1:
            signoff = existing[0]
        elif existing.count()>1:
            msg = 'Found too many existing signoffs. Something is wrong.'
            return HttpResponseServerError(msg)
    
        if not signoff:
            msg = 'Could not find existing signoff for this event/instrument.'
            return HttpResponseBadRequest(msg)

        # remove the existing label
        label_name = label_stem + signoff.status
        for l in event.labelling_set.all():
            if l.label.name == label_name:
                l.delete()

        delete = request.POST.get('delete', None)
        if delete:
            # delete the operator signoff object
            signoff.delete()

            # also restore the label
            create_label(event, request, req_label)

            # Create a log message
            msg = "deleted %s signoff status" % signoff_type
            if len(instrument):
                msg += ' for %s' % instrument
            logentry = EventLog.objects.create(event=event, issuer=request.user, comment=msg)

            # XXX Ugh. Hardcoding tagname here.
            # Add a tag to the log message
            try:
                tag = Tag.objects.get(name='em_follow')
                tag.eventlogs.add(logentry)
            except:
                pass
        else:
            if status==None:
                msg = "Please select a valid status."
                return HttpResponseBadRequest(msg)
            # update the values
            signoff.status = status
            signoff.comment = comment
            signoff.save()
            # Issue an alert.
            issueXMPPAlert(event, location='', alert_type="signoff", description=status, 
                serialized_object = signoffToDict(signoff))

            # Create a new label.
            label_name = label_stem + status
            create_label(event, request, label_name, doAlert=False, doXMPP=False)

            # Create a log message
            msg = "updated %s signoff status as %s" % (signoff_type, status)
            if len(instrument):
                msg += ' for %s' % instrument
            if comment:
                msg += ': %s' % comment
            logentry = EventLog.objects.create(event=event, issuer=request.user, comment=msg)

            # XXX Ugh. Hardcoding tagname here.
            # Add a tag to the log message
            try:
                tag = Tag.objects.get(name='em_follow')
                tag.eventlogs.add(logentry)
            except:
                pass

    # Finished. Redirect back to the event.
    return HttpResponseRedirect(reverse("view", args=[event.graceid()]))

