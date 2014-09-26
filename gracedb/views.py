
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
from forms import CreateEventForm, EventSearchForm, SimpleSearchForm

from django.contrib.auth.models import User

from view_logic import _createEventFromForm
from view_logic import get_performance_info
from view_utils import assembleLigoLw, get_file
from view_utils import flexigridResponse, jqgridResponse

import os
from django.conf import settings

from buildVOEvent import buildVOEvent

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import json

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

def voevent(request, graceid):
    event = Event.getByGraceid(graceid)
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

def logentry(request, graceid, num=None):
    try:
        event = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        raise Http404
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

    else:
        try:
            elog = event.eventlog_set.filter(N=num)[0]
        except Exception, e:
            raise Http404

    if not request.is_ajax():
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    rv = {}
    rv['comment'] = elog.comment
    rv['issuer'] = elog.issuer.username
    rv['created'] = elog.created.isoformat()
    rv['comment'] = elog.comment
    if tagname:
        rv['tagname'] = tagname

    return HttpResponse(json.dumps(rv), content_type="application/json")

def neighbors(request, graceid, delta1, delta2=None):
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

    try:
        event = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        raise Http404
    context['nearby'] = [(e.gpstime - event.gpstime, e)
                            for e in event.neighbors((delta1,delta2))]
    context['neighbor_delta'] = "[%+d,%+d]" % (delta1, delta2)
    return render_to_response(
        'gracedb/neighbors_frag.html',
        context,
        context_instance=RequestContext(request))

def view(request, graceid):
    context = {}
    try:
        a = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        raise Http404
    context['object'] = a
    context['eventdesc'] = get_file(graceid, "event.log")
    context['userdesc'] = get_file(graceid, "user.log")
    context['nearby'] = [(event.gpstime - a.gpstime, event)
                            for event in a.neighbors()]
#    context['skyalert_authorized'] = skyalert_authorized(request)
    context['blessed_tags'] = settings.BLESSED_TAGS
    context['single_inspiral_events'] = list(a.singleinspiral_set.all())
    context['neighbor_delta'] = "[%+d,%+d]" % (-5,5)
    # We need a new way of picking templates here. This is too gross.

    templates = ['gracedb/event_detail.html',]
    if a.pipeline.name in settings.COINC_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_coinc.html')
    elif a.pipeline.name in settings.GRB_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_GRB.html')
    elif a.pipeline.name.startswith('CWB'):
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


class LimitedEvent():
    def __init__(self, event):
        self._event = event
    def __getattr__(self, attr):
        if attr == 'gpstime':
            return None
        elif attr == 'created':
            return self._event.created.replace(second=0)
        else:
            return getattr(self._event, attr)


def latest_limited(request):
    return latest(request)

def latest(request):
    context = {}

    if request.method == "GET":
        form = SimpleSearchForm(request.GET)
    else:
        form = SimpleSearchForm(request.POST)

    template = 'gracedb/latest.html'
    if not request.user or not request.user.is_authenticated():
        limit = LimitedEvent
        template = 'gracedb/latest_public.html'
    else:
        limit = lambda x: x

    context['form'] = form
    context['rawquery'] = request.GET.get('query') or request.POST.get('query') or ""

    if form.is_valid():
        objects = form.cleaned_data['query'][0:50]
        context['objects'] = map(limit, objects)
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

def taglogentry(request, graceid, num, tagname):
    try:
        event = Event.getByGraceid(graceid)
        eventlog = event.eventlog_set.filter(N=num)[0]
    except:
        # Either the event or the log does not exist.
        raise Http404

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
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    # no need for a JSON response. 
    msg = "Successfully applied tag %s to log message %s." % (tagname, num)
    return HttpResponse(msg, content_type="text")

# XXX added by Branson. Performance metrics.

def performance(request):

    try:
        context = get_performance_info()
    except Exception, e:
        return HttpResponseServerError(str(e))

    return render_to_response(
            'gracedb/performance.html',
            context,
            context_instance=RequestContext(request))

# A view for the list of files associated with an event.
# We're deliberately leaving out the /general directory.
# The idea is to get rid of that horrible /gracedb-files/ url.
def file_list(request, graceid):
    try:
        event = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        return HttpResponseNotFound("Event not found")

    f = []
    for dirname, dirnames, filenames in os.walk(event.datadir()):
        f.extend(filenames)
        break

    context = {}
    context['file_list'] = f
    context['title'] = 'Files for %s' % graceid 
    context['graceid'] = graceid 
        
    return render_to_response(
        'gracedb/event_filelist.html',
        context,
        context_instance=RequestContext(request)) 


#------------------------------------------------------------------------------------------
# Old Stuff
#------------------------------------------------------------------------------------------
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
#        return False
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

