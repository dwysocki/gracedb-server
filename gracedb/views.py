
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound, Http404
from django.template import RequestContext
from django.core.urlresolvers import reverse, get_script_prefix
from django.shortcuts import render_to_response
from django.contrib.sites.models import Site
from django.utils.html import strip_tags, escape, urlize
from django.utils.safestring import mark_safe

from django.views.generic.list_detail import object_detail, object_list

from models import Event, Group, EventLog, Labelling, Label, User
from forms import CreateEventForm, EventSearchForm, SimpleSearchForm
from alert import issueAlert, issueAlertForLabel, issueAlertForUpdate
from translator import handle_uploaded_data

import urllib

import os

from buildVOEvent import buildVOEvent, submitToSkyalert

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

import simplejson

def index(request):
#   assert request.ligouser
    return render_to_response(
            'gracedb/index.html',
            {},
            context_instance=RequestContext(request))

def voevent(request, graceid):
    event = Event.getByGraceid(graceid)
    return HttpResponse(buildVOEvent(event), content_type="application/xml")

def skyalert(request, graceid):
    event = Event.getByGraceid(graceid)
    return HttpResponse(submitToSkyalert(event), content_type="text/plain")

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
    assert request.ligouser

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

def _createEventFromForm(request, form):
    saved = False
    warnings = []
    try:
        group = Group.objects.filter(name=form.cleaned_data['group'])
        type = form.cleaned_data['type']
        # Create Event
        event = Event()
        event.submitter = request.ligouser
        event.group = group[0]
        event.analysisType = type
        #  ARGH.  We don't get a graceid until we save,
        #  but we don't know in advance if we can actually
        #  create all the things we need for success!
        #  What to do?!
        event.save()
        saved = True  # in case we have to undo this.
        # Create data directory/directories
        #    Save uploaded file.
        dirPrefix = "/mnt/gracedb-web/data"
        eventDir = os.path.join(dirPrefix, event.graceid())
        os.mkdir( eventDir )
        os.mkdir( os.path.join(eventDir,"private") )
        os.mkdir( os.path.join(eventDir,"general") )
        #os.chmod( os.path.join(eventDir,"general"), int("041777",8) )
        os.chmod( os.path.join(eventDir,"general"), 041777 )
        f = request.FILES['eventFile']
        uploadDestination = os.path.join(eventDir, "private", f.name)
        fdest = open(uploadDestination, 'w')
        # Save uploaded file into user private area.
        for chunk in f.chunks():
            fdest.write(chunk)
        fdest.close()
        # Create WIKI page
        createWikiPage(event.graceid())

        # Extract Info from uploaded data
        # Temp (ha!) hack to deal with
        # out of band data from Omega to LUMIN.
        try:
            temp_data_loc = handle_uploaded_data(event, uploadDestination)
            try:
                # Send an alert.
                issueAlert(event,
                           os.path.join(event.clusterurl(), "private", f.name),
                           temp_data_loc)
            except Exception, e:
                warnings += ["Problem issuing an alert (%s)" % e]
        except Exception, e:
            warnings += ["Problem scanning data. No alert issued (%s)" % e]
        #return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
    except Exception, e:
        # something went wrong.
        # XXX We need to make sure we clean up EVERYTHING.
        # We don't.  Wiki page and data directories remain.
        # According to Django docs, EventLog entries cascade on delete.
        # Also, we probably want to keep track of what's failing
        # and send out an email (or something)
        if saved:
            # undo save.
            event.delete()
        warnings += ["Problem creating event (%s)" % e]
        event = None
    return event, warnings

def _saveUploadedFile(event, uploadedFile):
    # XXX Hardcoding.
    fname = os.path.join("/mnt/gracedb-web/data", event.graceid(), "private", uploadedFile.name)
    f = open(fname, "w")
    for chunk in uploadedFile.chunks():
        f.write(chunk)
    f.close()

def _createLog(request, graceid, comment, uploadedFile=None):
    response = HttpResponse(mimetype='application/json')
    rdict = {}

    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None

    if not event:
        rdict['error'] = "No such event id: %s" % graceid
    elif (not comment) and (not uploadedFile):
        rdict['error'] = "Missing argument(s)"
    else:
        logEntry = EventLog(event=event,
                            issuer=request.ligouser,
                            comment=comment)
        if uploadedFile:
            try:
                _saveUploadedFile(event, uploadedFile)
                logEntry.filename = uploadedFile.name
            except Exception, e:
                rdict['error'] = "Problem saving file: %s" % str(e)
        logEntry.save()

        if request.POST.get('alert') == "True":
            description = "LOG: "
            if uploadedFile:
                description = "UPLOAD: '%s' " % uploadedFile.name
            issueAlertForUpdate(event, description+comment, doxmpp=True)

    # XXX should be json
    rval = str(rdict)
    response['Content-length'] = len(rval)
    response.write(rval)
    return response

def upload(request):
    graceid = request.POST.get('graceid', None)
    comment = request.POST.get('comment', None)
    uploadedfile = request.FILES['upload']

    if 'cli_version' in request.POST:
        return _createLog(request, graceid, comment, uploadedfile)

    # else: old, old client
    response = HttpResponse(mimetype='text/plain')
    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None
    # uploadedFile.{name/chunks()}
    if not (comment and uploadedfile and graceid):
        msg = "ERROR: missing arg(s)"
    elif not event:
        msg = "ERROR: Event '%s' does not exist" % graceid
    else:
        #event issuer comment
        log = EventLog(event=event,
                       issuer=request.ligouser,
                       filename=uploadedfile.name,
                       comment=comment)
        try:
            log.save()
            msg = "OK"
        except:
            msg = "ERROR: problem creating log entry"
        try:
            # XXX
            # Badnesses:
            #   Same hardcoded path in multiple places.
            #   What if we're clobbering an existing file?
            fname = os.path.join("/mnt/gracedb-web/data", event.graceid(), "private", uploadedfile.name)
            f = open(fname, "w")
            for chunk in uploadedfile.chunks():
                f.write(chunk)
            f.close()
        except Exception, e:
            msg = "ERROR: could not save file " + fname + " " + str(e)
            log.delete()
    response = HttpResponse(mimetype='text/plain')
    response.write(msg)
    response['Content-length'] = len(msg)
    return response

def cli_tag(request):
    raise Exception("tag is not implemented.  Maybe you're thinking of 'label'?")
    graceid = request.POST.get('graceid')
    tagname = request.POST.get('tag')

    event = graceid and Event.getByGraceid(graceid)
    event.add_tag(tagname)

    msg = str({})
    response = HttpResponse(mimetype='application/json')
    response.write(msg)
    response['Content-length'] = len(msg)

    return response

def cli_label(request):
    graceid = request.POST.get('graceid')
    labelName = request.POST.get('label')

    d = {}
    event = graceid and Event.getByGraceid(graceid)
    
    try:
        label = Label.objects.filter(name=labelName)[0]
    except IndexError:
        raise ValueError("No such Label '%s'" % labelName)

    # Don't add a label more than once.
    if label in event.labels.all():
            d['warning'] = "Event %s already labeled with '%s'" % (event.graceid(), labelName)
    else:
        labelling = Labelling(
                event = event,
                label = label,
                creator = request.ligouser
            )
        labelling.save()
        message = "Label: %s" % label.name
        log = EventLog(event=event, issuer=request.ligouser, comment=message)
        log.save()

        try:
            doxmpp = request.POST.get('alert') == "True"
            issueAlertForLabel(event, label, doxmpp)
        except Exception, e:
            d['warning'] = "Problem issuing alert (%s)" % str(e)

    msg = str(d)
    response = HttpResponse(mimetype='application/json')
    response.write(msg)
    response['Content-length'] = len(msg)

    return response

def log(request):
    message = request.POST.get('message')
    graceid = request.POST.get('graceid')

    if 'cli_version' in request.POST:
        return _createLog(request, graceid, message)

    # old, old client only
    response = HttpResponse(mimetype='text/plain')
    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None

    if not (message and graceid):
        msg = "ERROR: missing arg(s)"
    elif not event:
        msg = "ERROR: Event '%s' does not exist" % graceid
    else:
        #event issuer comment
        log = EventLog(event=event, issuer=request.ligouser, comment=message)
        try:
            log.save()
            msg = "OK"
        except:
            msg = "ERROR: problem creating log entry"

    response = HttpResponse(mimetype='text/plain')
    response.write(msg)
    response['Content-length'] = len(msg)
    return response

def ping(request):
    #ack = "(%s) " % Site.objects.get_current()
    ack = "(%s) " % request.META['SERVER_NAME']
    ack += request.POST.get('ack', None) or request.GET.get('ack','ACK')

    from templatetags.timeutil import utc
    if 'cli_version' in request.POST:
        response = HttpResponse(mimetype='application/json')
        d = {'output': ack}
        if 'extended' in request.POST:
            latest = Event.objects.order_by("-id")[0]
            d['latest'] = {}
            d['latest']['id'] = latest.graceid()
            d['latest']['created'] = str(utc(latest.created))
        d =  simplejson.dumps(d)
        response.write(d)
        response['Content-length'] = len(d)
    else:
        # Old client
        response = HttpResponse(mimetype='text/plain')
        response.write(ack)
        response['Content-length'] = len(ack)
    return response

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
    return render_to_response(
        'gracedb/event_detail.html',
        context,
        context_instance=RequestContext(request))

def cli_search(request):
    assert request.ligouser
    form = SimpleSearchForm(request.POST)
    if form.is_valid():
        query = form.cleaned_data['query']
        objects = Event.objects.filter(query).distinct()
        # Assemble the output... should be able to choose format.
        outTable = ["#graceid\tlabels\tgroup\ttype\tgpstime\tcreatetime\turl"]
        outTable += [
            "%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
                e.graceid(),
                ",".join([labelling.label.name for labelling in e.labelling_set.all()]),
                e.group,
                e.get_analysisType_display(),
                e.gpstime or "",
                e.created,
                e.weburl(),
            )
            for e in objects
        ]
        d = {'output': "\n".join(outTable)}
    else:
        d = {'error': ""}
        for key in form.errors:
            d['error'] += "%s: %s\n" % (key, strip_tags(form.errors[key]))
    response = HttpResponse(mimetype='application/javascript')
    msg = simplejson.dumps(d)
    response['Content-length'] = len(msg)
    response.write(msg)
    return response

def search(request, format=""):
    assert request.ligouser
    # XXX DO NOT HARDCODE THIS
    # Also, user should be notified if their result hits this limit.
    limit = MAX_QUERY_RESULTS
    form2 = None

    # This block is crap and for debugging.  Remove it!
    if False and format == "flex":
        response = HttpResponse(mimetype='application/json')
        rows = [
                { 'id': 1, 'cell': 
                    [ "G0966", "", "CBC", "MBTAOnline", 9382382, "Data Wiki", "today!"]
                    },
                { 'id': 2, 'cell':
                    [ "G0967", "", "CBC", "MBTAOnline", 9382382, "Data Wiki", "today!"]
                    },
                { 'id': 3, 'cell':
                    [ "G0968", "", "CBC", "MBTAOnline", 9382382, "Data Wiki", "today!"]
                    },
            ]
        d = {
                'page': 1, #self.page,
                'total': 1,
                'records' : 3,
                'rows': rows
            }
        msg = simplejson.dumps(d)
        response['Content-length'] = len(msg)
        response.write(msg)

        #query = request.POST['query']
        # ???!!!
        query = "blah"

        return response

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
            query = form.cleaned_data['query']

            objects = Event.objects.filter(query).distinct()

            if format == "json":
                return HttpResponse("Not Implemented")
            elif format == "flex":
                # Flexigrid request.
                return flexigridResponse(request, objects)
            elif format == "jqgrid":
                return jqgridResponse(request, objects)
            else:
                #objects = objects[:limit]
                #if objects.count() >= limit:
                #    request.session['flash_msg'] = \
                #        "Number of events in results exceeds maximum (%s) allowed." % limit
                if objects.count() == 1:
                    title = "Query Results. %s event" % objects.count()
                else:
                    title = "Query Results. %s events" % objects.count()
                context = {
                    'title': title,
                    'form': form,
                    'formAction': reverse(search),
                    'maxCount': limit,
                    'rawquery' : rawquery,
                }
                return object_list(request, objects, extra_context=context)
    return render_to_response('gracedb/query.html',
            { 'form' : form,
              'form2' : form2,
            },
            context_instance=RequestContext(request))

def oldsearch(request):
    assert request.ligouser
    if request.method == 'GET':
        form = EventSearchForm()
    else:
        form = EventSearchForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['graceidStart']
            end = form.cleaned_data['graceidEnd']
            submitter = form.cleaned_data['submitter']
            groupname = form.cleaned_data['group']
            typename = form.cleaned_data['type']
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
            if typename:
                objects = objects.filter(analysisType=typename)
                textQuery.append("type: %s" % Event.getTypeLabel(typename))

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
            extra_context = {'title': title }

            textQuery = " ".join(textQuery)
            simple_form = SimpleSearchForm({'query': textQuery})
            extra_context['form'] = simple_form
            extra_context['maxCount'] = MAX_QUERY_RESULTS
            extra_context['rawquery' ] = textQuery

            return object_list(request, objects, extra_context=extra_context)


    return render_to_response('gracedb/query.html',
            { 'form' : form },
            context_instance=RequestContext(request))

def timeline(request):
    from gracedb.utils import gpsToUtc
    from django.utils import dateformat

    response = HttpResponse(mimetype='application/javascript')
    events = []
    for event in Event.objects.exclude(group__name="Test").all():
        if event.gpstime:
            t = dateformat.format(gpsToUtc(event.gpstime), "F j, Y h:i:s")+" UTC"

            events.append({
                'start': t,
                'title': event.get_analysisType_display(),
                'description':
                    "%s<br/>%s" %(event.get_analysisType_display(),"GPS time:%s"%event.gpstime),
                'durationEvent':False,
              })
    d = {'events': events}
    msg = simplejson.dumps(d)
    response['Content-length'] = len(msg)
    response.write(msg)
    return response

#-----------------------------------------------------------------
# Things that aren't views and should really be elsewhere.
#-----------------------------------------------------------------

from templatetags.timeutil import timeSelections

def jqgridResponse(request, objects):
    # "GET /data?_search=false&nd=1266350238476&rows=10&page=1&sidx=invid&sord=asc HTTP/1.1"
    pass

def flexigridResponse(request, objects):
    response = HttpResponse(mimetype='application/json')

    #sortname = request.POST.get('sortname', None)
    #sortorder = request.POST.get('sortorder', 'desc')
    #page = int(request.POST.get('page', 1))
    #rp = int(request.POST.get('rp', 10))

    sortname = request.GET.get('sidx', None)    # get index row - i.e. user click to sort
    sortorder = request.GET.get('sord', 'desc') # get the direction
    page = int(request.GET.get('page', 1))      # get the requested page
    rp = int(request.GET.get('rows', 10))       # get how many rows we want to have into the grid

    if sortname:
        if sortorder == "desc":
            sortname = "-" + sortname
        objects = objects.order_by(sortname)

    start = (page-1) * rp
    rows = []
    total = objects.count()

    if total:
        total_pages = (total / rp) + 1
    else:
        total_pages = 0

    if page > total_pages:
        page = total_pages

    for object in objects[start:start+rp]:
        event_times = timeSelections(object.gpstime)
        created_times = timeSelections(object.created)
        rows.append(
            { 'id' : object.id,
              'cell': [ '<a href="%s">%s</a>' %
                            (reverse(view, args=[object.graceid()]), object.graceid()),
                         #Labels
                        " ".join(['<span title="%s %s" style="color: %s">%s</span>' %
                                (label.creator.name, label.created, label.label.defaultColor, label.label.name)
                                for label in object.labelling_set.all()
                            ]),
                        # Links to neighbors
                        ', '.join([
                            '<a href="%s">%s</a>' %
                            (reverse(view, args=[n.graceid()]), n.graceid())
                            for n in object.neighbors()
                        ]),
                        object.group.name,
                        object.get_analysisType_display(),

                        event_times.get('gps',""),
                        #event_times['utc'],

                        '<a href="%s">Data</a> <a href="%s">Wiki</a>' %
                            (object.weburl(), object.wikiurl()),

                        #created_times['gps'],
                        created_times.get('utc',""),

                        object.submitter.name,

                      ]
            }
        )
    d = {
            'page': page,
            'total': total_pages,
            'records': total,
            'rows': rows,
        }
    try:
        msg = simplejson.dumps(d)
    except Exception, e:
        # XXX Not right not right not right.
        msg = "{}"
    response['Content-length'] = len(msg)
    response.write(msg)

    #query = request.POST['query']

    return response

def get_file(graceid, filename="event.log"):
    dirPrefix = "/mnt/gracedb-web/data"
    logfilename = os.path.join(dirPrefix, graceid, "private", filename)
    contents = ""
    try:
        lines = open(logfilename, "r").readlines()
        contents = "<br/>".join([ escape(line) for line in lines])
        contents = mark_safe(urlize(contents))
    except Exception, e:
        contents = None
    return contents

def createWikiPage(graceid):
    # Do not create wiki pages these reasons
    # (1) freaks out the wiki/filesystem to have too many files in one directory.
    # (2) do not need them if they are empty. They'll be auto-created if ppl go to them and want them.
    # (3) htdocs (where the wikipage goes) is mounted read-only.
    return
    twikiroot = "/mnt/htdocs/uwmlsc/secure/twiki/data/Sandbox/"
    plainFile = """
Initial Entry for %s

%%TOC{depth="2"}%%
""" % graceid
    rcsFile = """head    1.1;
access; 
symbols;
locks
    apache:1.1; strict;
comment @# @;


1.1
date    2009.06.13.00.09.15;    author apache;    state Exp;
branches;
next    ;


desc
@Initial Revision
@


1.1
log
@Initial revision
@
text
@
Initial Entry for %s

%%TOC{depth="2"}%%
@
""" % graceid
    pname = os.path.join(twikiroot, graceid+".txt")
    rcsname = os.path.join(twikiroot, graceid+".txt,r")
    f = open(pname, "w")
    f.write(plainFile)
    f.close()

    f = open(rcsname, "w")
    f.write(rcsFile)
    f.close()

    os.chmod(pname, 0644)
    os.chmod(rcsname, 0444)

