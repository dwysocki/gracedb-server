
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template import RequestContext
from django.core.urlresolvers import reverse, get_script_prefix
from django.shortcuts import render_to_response
from django.contrib.sites.models import Site

from django.views.generic.list_detail import object_detail, object_list

from models import Event, Group, EventLog
from forms import CreateEventForm, EventSearchForm
from alert import issueAlert
from translator import handle_uploaded_data

import os

def index(request):
#   assert request.ligouser
    return render_to_response(
            'gracedb/index.html',
            {},
            context_instance=RequestContext(request))

def create(request):
    assert request.ligouser

    if request.method == "GET":
        form = CreateEventForm()
    else:
        form = CreateEventForm(request.POST, request.FILES)
        saved = False
        if form.is_valid():
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
                handle_uploaded_data(event, uploadDestination)

                # Send an alert.
                issueAlert(event, os.path.join(event.clusterurl(), "private", f.name))
                #return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
            except:
                # something went wrong.
                # XXX We need to make sure we clean up EVERYTHING.
                # We don't.  Wiki page and data directories remain.
                # According to Django docs, EventLog entries cascade on delete.
                # Also, we probably want to keep track of what's failing
                # and send out an email (or something)
                if saved:
                    # undo save.
                    event.delete()
                raise
            if 'cli' in request.POST:
                msg = str(event.graceid())
                response = HttpResponse(mimetype='text/plain')
                response.write(msg)
                response['Content-length'] = len(msg)
                return response
            return HttpResponseRedirect(reverse(view, args=[event.graceid()]))
        else: # form not valid
            if 'cli' in request.POST:
                # Error occurred in command line client.
                # Most likely group name is wrong.
                # XXX the form should have info about what is wrong.
                groupname = request.POST.get('group', None)
                group = Group.objects.filter(name=groupname)
                if not group:
                    validGroups = [group.name for group in Group.objects.all()]
                    msg = "ERROR: group must be one of: %s" % ", ".join(validGroups)
                else:
                    msg = "ERROR: malformed request"
                response = HttpResponse(mimetype='text/plain')
                response.write(msg)
                response['Content-length'] = len(msg)
                return response

            # if not a command line request, let it fall through
    return render_to_response('gracedb/create.html',
                { 'form' : form },
                context_instance=RequestContext(request))

def upload(request):
    graceid = request.POST.get('graceid', None)
    comment = request.POST.get('comment', None)
    uploadedfile = request.FILES['upload']
    response = HttpResponse(mimetype='text/plain')
    event = graceid and Event.getByGraceid(graceid)
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

def log(request):
    message = request.POST.get('message')
    graceid = request.POST.get('graceid')
    response = HttpResponse(mimetype='text/plain')
    event = graceid and Event.getByGraceid(graceid)
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
    ack = "(%s) " % Site.objects.get_current()
    ack += request.POST.get('ack', None) or request.GET.get('ack','ACK')
    response = HttpResponse(mimetype='text/plain')
    response.write(ack)
    response['Content-length'] = len(ack)
    return response

def view(request, graceid):
    context = {}
    a = Event.getByGraceid(graceid)
    if not a:
        return HttpResponseNotFound()
    context['object'] = a
    return render_to_response(
        'gracedb/event_detail.html',
        context,
        context_instance=RequestContext(request))

def search(request):
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
            gpsStart =  form.cleaned_data['gpsStart']
            slop =  form.cleaned_data['gpsSlop']

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

            if gpsStart:
                slop = slop or 0
                if not slop:
                    objects = objects.filter(gpstime=gpsStart)
                else:
                    gpsStart = int(gpsStart)
                    slop = int(slop) / 2
                    objects = objects.filter(gpstime__gte=gpsStart-slop)
                    objects = objects.filter(gpstime__lte=gpsStart+slop)

            if submitter:
                objects = objects.filter(submitter=submitter)
            if groupname:
                group = Group.objects.filter(name=groupname)[0]
                objects = objects.filter(group=group)
            if typename:
                objects = objects.filter(analysisType=typename)
            if form.cleaned_data['ligoApproved']:
                objects = objects.filter(approval__approvingCollaboration='L')
            if form.cleaned_data['virgoApproved']:
                objects = objects.filter(approval__approvingCollaboration='V')

            return object_list(request, objects, extra_context={'title':"Query Results"})


    return render_to_response('gracedb/query.html',
            { 'form' : form },
            context_instance=RequestContext(request))

#-----------------------------------------------------------------
# Things that aren't views and should really be elsewhere.
#-----------------------------------------------------------------

def createWikiPage(graceid):
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

