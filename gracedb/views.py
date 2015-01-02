
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest, Http404
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response

# Upgrade to Django 1.5: No more function-based generic views.
#from django.views.generic.list_detail import object_list
from django.views.generic.list import ListView

from models import Event, Group, EventLog, Label, Tag, Pipeline, Search
from models import EMGroup
from forms import CreateEventForm, EventSearchForm, SimpleSearchForm

from django.contrib.auth.models import User, Permission
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from permission_utils import filter_events_for_user, user_has_perm
from permission_utils import internal_user_required
from guardian.models import GroupObjectPermission

from view_logic import _createEventFromForm
from view_logic import get_performance_info
from view_logic import get_lvem_perm_status
from view_logic import create_eel
from view_utils import assembleLigoLw, get_file
from view_utils import flexigridResponse, jqgridResponse

import os
from django.conf import settings

from buildVOEvent import buildVOEvent

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import json
from django.utils.functional import wraps

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
    return render_to_response(
            'gracedb/index.html',
            {},
            context_instance=RequestContext(request))

# SP Info and Privacy pages are required for Federation with InCommon. 
def spinfo(request):
    return render_to_response('gracedb/spinfo.html', {}, context_instance=RequestContext(request))

def spprivacy(request):
    return render_to_response('gracedb/spprivacy.html', {}, context_instance=RequestContext(request))

def discovery(request):
    return render_to_response('discovery.html', {}, context_instance=RequestContext(request))

@event_and_auth_required
def voevent(request, event):
    if not event.far or not event.gpstime:
        # can't build VOEvent without a FAR or GPS time
        message = "Cannot build a VOEvent."
        if not event.far:
            message += " Event has no FAR."
        if not event.gpstime:
            message += " Event has no GPS time."
        return render_to_response(
                '404.html',
                {"message":message},
                context_instance=RequestContext(request))
    voevent = buildVOEvent(event, request)
    return HttpResponse(voevent, content_type="application/xml")

def create(request):
    d = _create(request)
    if isinstance(d, HttpResponse):
        return d
    elif 'cli' in request.POST:
        if 'cli_version' in request.POST:
            # XXX Risky.  msg should be json, not str.
            # str(x) is *often* the same as json(x), but not always.
            # It's not, because we don't reliably have json on the client side.
            response = HttpResponse(mimetype='application/json')
            if 'graceid' in d:
                d['output'] = "%s" % d['graceid']
                d['graceid'] = "%s" % d['graceid']
            msg = str(d)
        else: # Old client
            response = HttpResponse(mimetype='text/plain')
            if 'error' in d:
                msg = "ERROR: " + d['error']
            elif 'warning' in d:
                msg = "ERROR: " + d['warning']
            else:
                msg = d['graceid']
        response.write(msg)
        response['Content-length'] = len(msg)
        return response
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
            if 'cli' not in request.POST:
                if not event:
                    # problem creating event...  XXX need an error page for this.
                    raise Exception("\n".join(warnings))
                return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
            if event:
                rv['graceid'] = str(event.graceid())
                if warnings:
                    rv['warning'] = "\n".join(warnings)
            else:
                rv['error'] = "\n".join(warnings)
        else:
            if 'cli' not in request.POST:
                rv['form'] = form
            else:
                # Error occurred in command line client.
                # Most likely group name is wrong.
                # XXX the form should have info about what is wrong.
                #groupname = request.POST.get('group', None)
                #group = Group.objects.filter(name=groupname)
                #if not group:
                #    validGroups = [group.name for group in Group.objects.all()]
                #    msg = "Group must be one of: %s" % ", ".join(validGroups)
                #else:
                #    msg = "Malformed request"
                #rv['error'] = msg
                rv['error'] = ""
                for key in form.errors:
                    # as_text() not str() otherwise we get HTML.
                    rv['error'] += "%s: %s\n" % (key, form.errors[key].as_text())
    return rv

@event_and_auth_required
def logentry(request, event, num=None):
    if request.method == "POST":
        # create a log entry
        elog = EventLog(event=event, issuer=request.user)
        elog.comment = request.POST.get('comment') or request.GET.get('comment')
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

    elif request.method == "GET":
        if not user_has_perm(request.user, 'view', event):
            return HttpResponseForbidden("Forbidden")
        try:
            elog = event.eventlog_set.filter(N=num)[0]
        except Exception, e:
            raise Http404
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
    context['eventdesc'] = get_file(event.graceid(), "event.log")
    context['userdesc'] = get_file(event.graceid(), "user.log")
    context['nearby'] = [(e.gpstime - event.gpstime, e)
                            for e in event.neighbors()]
#    context['skyalert_authorized'] = skyalert_authorized(request)
    context['groups'] = [g.name for g in EMGroup.objects.all()]
    context['blessed_tags'] = settings.BLESSED_TAGS
    context['single_inspiral_events'] = list(event.singleinspiral_set.all())
    context['neighbor_delta'] = "[%+d,%+d]" % (-5,5)
    context['SKYMAP_VIEWER_SERVICE_URL'] = settings.SKYMAP_VIEWER_SERVICE_URL

    # XXX This is something of a hack. In the future, we will want to show the
    # executive user a list of groups and a two column list of radio buttons, showing
    # whether the group has access to this event or not, along with a submit button
    # at the bottom to commit changes. But for ER6, we won't need all that structure.
    can_expose_to_lvem, can_protect_from_lvem = get_lvem_perm_status(request,event)
    context['can_expose_to_lvem'] = can_expose_to_lvem
    context['can_protect_from_lvem'] = can_protect_from_lvem
    lvem_group_name = ''
    try:
        lvem_group_name = AuthGroup.objects.get(name__contains='LV-EM').name
    except:
        pass
    context['lvem_group_name'] = lvem_group_name

    # Choose your template according to the event's pipeline.
    templates = ['gracedb/event_detail.html',]
    if event.pipeline.name in settings.COINC_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_coinc.html')
    elif event.pipeline.name in settings.GRB_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_GRB.html')
    elif event.pipeline.name.startswith('CWB'):
        templates.insert(0, 'gracedb/event_detail_CWB.html')

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
        if form.is_valid():
            objects = form.cleaned_data['query']

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

                xmldoc = assembleLigoLw(objects)

                response = HttpResponse(mimetype='application/xml')
                response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
                utils.write_fileobj(xmldoc, response)
                return response

            else:
                #objects = objects[:limit]
                #if objects.count() >= limit:
                #    request.session['flash_msg'] = \
                #        "Number of events in results exceeds maximum (%s) allowed." % limit
                if objects.count() == 1:
                    title = "Query Results. %s event" % objects.count()
                else:
                    title = "Query Results. %s events" % objects.count()
                # XXX This seems like a hacky misuse of generic views.
                # In Django 1.3 and earlier, things were simpler:
                #
                # return object_list(request, objects, extra_context=context)
                # 
                # But with for compatibility, with Django 1.6, this becomes:
                class EventListView(ListView):
                    queryset = objects
                    template_name = "gracedb/event_list.html"

                    def dispatch(self, request, *args, **kwargs):
                        # NOTE: We have to hack around the handler selector, because
                        # the actual request might have been a POST.
                        handler = getattr(self, 'get', self.http_method_not_allowed)
                        return handler(request, *args, **kwargs)

                    # This is how to get the extra context in, according to the django docs.
                    def get_context_data(self, **kwargs):
                        context = super(EventListView, self).get_context_data(**kwargs)
                        # Insert the extra context.
                        context.update({
                            'title'      : title,
                            'form'       : form,
                            'formAction' : reverse(search),
                            'maxCount'   : limit,
                            'rawquery'   : rawquery,
                        })
                        return context

                return EventListView.as_view()(request)

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

            textQuery = []

            if not groupname:
                # don't show test events unless explicitly requested
                # Scales?  Or should we find test group and do group= ?
                objects = Event.objects.exclude(group__name='Test')
            else:
                objects = Event.objects.all()

            if start:
                if start[0] != 'G':
                    # XXX This is the deprecated uid stuff. Take it out when uid is gone.
                    objects = objects.filter(uid__gte=start)
                    objects = objects.filter(uid__startswith="0")
                else:
                    objects = objects.filter(id__gte=int(start[1:]))
                    objects = objects.filter(uid="")
            if end:
                if end[0] != 'G':
                    # XXX This is the deprecated uid stuff. Take it out when uid is gone.
                    objects = objects.filter(uid__lte=end)
                    objects = objects.filter(uid__startswith="0")
                else:
                    objects = objects.filter(id__lte=int(end[1:]))
                    objects = objects.filter(uid="")

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

            # XXX This seems like a hacky misuse of generic views.
            # In Django 1.3 and earlier, things were simpler:
            #
            # return object_list(request, objects, extra_context=context)
            # 
            # But with for compatibility, with Django 1.6, this becomes:
            class EventListView(ListView):
                queryset = objects
                template_name = "gracedb/event_list.html"

                def dispatch(self, request, *args, **kwargs):
                    # NOTE: We have to hack around the handler selector, because
                    # the actual request might have been a POST.
                    handler = getattr(self, 'get', self.http_method_not_allowed)
                    return handler(request, *args, **kwargs)

                # This is how to get the extra context in, according to the django docs.
                def get_context_data(self, **kwargs):
                    context = super(EventListView, self).get_context_data(**kwargs)
                    # Insert the extra context.
                    context.update({
                        'title'      : title,
                        'form'       : simple_form,
                        'maxCount'   : MAX_QUERY_RESULTS,
                        'rawquery'   : textQuery,
                    })
                    return context

            return EventListView.as_view()(request)


    return render_to_response('gracedb/query.html',
            { 'form' : form },
            context_instance=RequestContext(request))

def latest(request):
    context = {}

    if request.method == "GET":
        form = SimpleSearchForm(request.GET)
    else:
        form = SimpleSearchForm(request.POST)

    template = 'gracedb/latest.html'
    context['form'] = form
    context['rawquery'] = request.GET.get('query') or request.POST.get('query') or ""

    if form.is_valid():
        objects = form.cleaned_data['query']
        objects = filter_events_for_user(objects, request.user, 'view')[0:50]
        context['objects'] = objects
        context['error'] = False
    else:
        context['error'] = True

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
# We're deliberately leaving out the /general directory.
# The idea is to get rid of that horrible /gracedb-files/ url.
#
@event_and_auth_required
def file_list(request, event):
    f = []
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

    # Get the group
    try:
        g = AuthGroup.objects.get(name=group_name)
    except Group.DoesNotExist:
        return HttpResponseNotFound('Group not found')

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
            content_type=ctype, group=g, permission=view,
            object_pk=event.id)
        GroupObjectPermission.objects.get_or_create(
            content_type=ctype, group=g, permission=change,
            object_pk=event.id)
    elif action=='protect':
        # Retrieve both group object permissions
        # Delete them
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=ctype, group=g, permission=change,
                object_pk=event.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass
        try:
            gop = GroupObjectPermission.objects.get(
                content_type=ctype, group=g, permission=view,
                object_pk=event.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass
    else:
        msg = "Unknown action. Choices are 'expose' and 'protect'."
        return HttpResponseBadRequest(msg)

    # Finished. Redirect back to the event.
    return HttpResponseRedirect(reverse("view", args=[event.graceid()]))

from hashlib import md5

# A view to create embb log entries
@event_and_auth_required
def embblogentry(request, event, num=None):
    if request.method == "POST":
        try:
            eel = create_eel(request.POST, event, request.user)
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

#------------------------------------------------------------------------------------------
# Old Stuff
#------------------------------------------------------------------------------------------
#
# Here is the old stuff we used for the Latest page.
# Originally, public users could see a version of this page with some
# fields stripped out. We may still want to do something like that in the 
# future, but for now, we're actually limiting *which* events a public user
# can see. 
#
#class LimitedEvent():
#    def __init__(self, event):
#        self._event = event
#    def __getattr__(self, attr):
#        if attr == 'gpstime':
#            return None
#        elif attr == 'created':
#            return self._event.created.replace(second=0)
#        else:
#            return getattr(self._event, attr)
#
#def latest_limited(request):
#    return latest(request)
#
#def latest(request):
#    context = {}
#
#    if request.method == "GET":
#        form = SimpleSearchForm(request.GET)
#    else:
#        form = SimpleSearchForm(request.POST)
#
#    template = 'gracedb/latest.html'
#    if not request.user or not request.user.is_authenticated():
#        limit = LimitedEvent
#        template = 'gracedb/latest_public.html'
#    else:
#        limit = lambda x: x
#
#    context['form'] = form
#    context['rawquery'] = request.GET.get('query') or request.POST.get('query') or ""
#
#    if form.is_valid():
#        objects = form.cleaned_data['query']
#        objects = filter_events_for_user(objects, request.user, 'view')[0:50]
#        context['objects'] = map(limit, objects)
#        context['error'] = False
#    else:
#        context['error'] = True
#
#    return render_to_response(
#            template,
#            context,
#            context_instance=RequestContext(request))
#
#
# XXX This looks interesting. Apparently an old attempt by Brian to make a nice 
# graphical timeline of events, a la SkyAlert. Or something?
#def timeline(request):
#    from utils import gpsToUtc
#    from django.utils import dateformat
#
#    response = HttpResponse(mimetype='application/javascript')
#    events = []
#    for event in Event.objects.exclude(group__name="Test").all():
#        if event.gpstime:
#            t = dateformat.format(gpsToUtc(event.gpstime), "F j, Y h:i:s")+" UTC"
#
#            events.append({
#                'start': t,
#                'title': event.get_analysisType_display(),
#                'description':
#                    "%s<br/>%s" %(event.get_analysisType_display(),"GPS time:%s"%event.gpstime),
#                'durationEvent':False,
#              })
#    d = {'events': events}
#    msg = json.dumps(d)
#    response['Content-length'] = len(msg)
#    response.write(msg)
#    return response
#
#import re
#from django.core.mail import mail_admins
#from buildVOEvent import submitToSkyalert
#
#def skyalert_authorized(request):
#    try:
#        return u"{0} {1}".format(request.user.first_name, request.user.last_name) in settings.SKYALERT_SUBMITTERS
#    except:
#        return Fals
#
#def skyalert(request, graceid):
#    event = Event.getByGraceid(graceid)
#    createLogEntry = True
#
#    if not event.gpstime:
#        request.session['flash_msg'] = "No GPS time.  Event not suitable for submission to SkyAlert"
#        return HttpResponseRedirect(reverse(view, args=[graceid]))
#
#    if not event.far:
#        request.session['flash_msg'] = "No FAR.  Event not suitable for submission to SkyAlert"
#        return HttpResponseRedirect(reverse(view, args=[graceid]))
#
#    if not skyalert_authorized(request):
#        request.session['flash_msg'] = "You are not authorized for SkyAlert submission"
#        return HttpResponseRedirect(reverse(view, args=[graceid]))
#
#    try:
#        skyalert_response = submitToSkyalert(event)
#    except Exception, e:
#        message = "SkyAlert Submission Error"
#        skyalert_response = ""
#        # XXX umm.  don't we want to know if this email fails silently?
#        mail_admins("SkyAlert Submission Error",
#                    "Event: %s\nException: %s\n" % (graceid, e),
#                    fail_silently=True)
#
#    flashmessage = None
#    if skyalert_response.find("Success") >= 0:
#        urlpat = re.compile('https?://[^ ]*')
#        match = urlpat.search(skyalert_response)
#        if match:
#            message = "Submitted to Skyalert: %s" % match.group()
#            url = match.group()
#            flashmessage = 'Submitted to Skyalert: %s' % url
#            message = 'Submitted to Skyalert: <a href="%s">%s</a>' % (url,url)
#        else:
#            message = "SkyAlert submission problem.  Cannot parse SkyAlert response."
#            # XXX umm.  don't we want to know if this email fails silently?
#            mail_admins("SkyAlert response parsing problem",
#                        "Event: %s\nSkyAlert Response: %s\n" % (graceid, skyalert_response),
#                        fail_silently=True)
#    elif (skyalert_response.find('already') >= 0) or (skyalert_response.find('Duplicate') >= 0):
#            message = "Event already submitted to SkyAlert"
#            createLogEntry = False
#    elif skyalert_response:
#        message = "Skyalert Submission Failed."
#        mail_admins("SkyAlert submission failed",
#                    "Event: %s\nSkyAlert Response: %s\n" % (graceid, skyalert_response),
#                    fail_silently=True)
#
#    request.session['flash_msg'] = flashmessage or message
#
#    if createLogEntry:
#        logentry = EventLog(event=event, issuer=request.ligouser, comment=message)
#        try:
#            logentry.save()
#        except:
#            # XXX Failed to create log entry for skyalert submission.
#            # Error message?
#            pass
#
#    return HttpResponseRedirect(reverse(view, args=[graceid]))
#


