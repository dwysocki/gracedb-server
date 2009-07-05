
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template import RequestContext
from django.core.urlresolvers import reverse, get_script_prefix
from django.shortcuts import render_to_response

from django.views.generic.list_detail import object_detail, object_list

from models import Event, Group
from forms import CreateEventForm, EventSearchForm
from alert import issueAlert

import os

def index(request):
#   assert request.ligouser
    return render_to_response(
            'gracedb/index.html',
#           {'hi':request.ligouser},
            {},
            context_instance=RequestContext(request))

def create(request):
    assert request.ligouser

    if request.method == "GET":
        form = CreateEventForm()
    else:
        form = CreateEventForm(request.POST, request.FILES)
        if form.is_valid():
            group = Group.objects.filter(name=form.cleaned_data['group'])
            type = form.cleaned_data['type']
            # Create Event
            event = Event()
            event.submitter = request.ligouser
            event.group = group[0]
            event.analysisType = type
            # Create data directory/directories
            #    Save uploaded file.
            dirPrefix = "/mnt/gracedb-web/data"
            eventDir = os.path.join(dirPrefix, event.uid)
            os.mkdir( eventDir )
            os.mkdir( os.path.join(eventDir,"private") )
            os.mkdir( os.path.join(eventDir,"general") )
            #os.chmod( os.path.join(eventDir,"general"), int("041777",8) )
            os.chmod( os.path.join(eventDir,"general"), 041777 )
            f = request.FILES['eventFile']
            uploadDestination = os.path.join(eventDir, "private", f.name)
            fdest = open(uploadDestination, 'w')
            # XXX probably want to check exit code
            # Oh.  and it doesn't work.
            os.system("/usr/bin/sudo /usr/local/bin/fixgracedirs %s >/dev/null" % event.uid)
            #fdest.write("[%s] %s bytes\n" % (f.name, f.size))

            # Save uploaded file into user private area.
            for chunk in f.chunks():
                fdest.write(chunk)
            fdest.close()
            # Create WIKI page
            createWikiPage(event.uid)
            event.save()  # if everything worked... save.
            # Send an alert.
            issueAlert(event, os.path.join(event.clusterurl(), "private", f.name))
            #return HttpResponseRedirect(reverse(view, args=[event.uid]))
            if 'cli' in request.POST:
                msg = str(event.uid)
                response = HttpResponse(mimetype='text/xml')
                response.write(msg)
                response['Content-length'] = len(msg)
                return response
            return HttpResponseRedirect(reverse(search))
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
                    response = HttpResponse(mimetype='text/xml')
                    response.write(msg)
                    response['Content-length'] = len(msg)
                    return response

            # if not a command line request, let it fall through
    return render_to_response('gracedb/create.html',
                { 'form' : form },
                context_instance=RequestContext(request))


def search(request):
    assert request.ligouser
    if request.method == 'GET':
        form = EventSearchForm()
    else:
        form = EventSearchForm(request.POST)
        if form.is_valid():
            objects = Event.objects.all()
            start = form.cleaned_data['uidStart']
            end = form.cleaned_data['uidEnd']
            submitter = form.cleaned_data['submitter']
            groupname = form.cleaned_data['group']
            typename = form.cleaned_data['type']
            if start:
                objects = objects.filter(uid__gte=start)
            if end:
                objects = objects.filter(uid__lte=end)
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

def createWikiPage(uid):
    twikiroot = "/mnt/htdocs/uwmlsc/secure/twiki/data/Sandbox/"
    plainFile = """
Initial Entry for %s

%%TOC{depth="2"}%%
""" % uid
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
""" % uid
    pname = os.path.join(twikiroot, uid+".txt")
    rcsname = os.path.join(twikiroot, uid+".txt,r")
    f = open(pname, "w")
    f.write(plainFile)
    f.close()

    f = open(rcsname, "w")
    f.write(rcsFile)
    f.close()

    os.chmod(pname, 0644)
    os.chmod(rcsname, 0444)

        #  f=open(twikiroot+eventid+".txt","w")
        #  entry=[]
        #  entry.append('%TOC{depth="2"}%\n')
        #  entry.append('---+ Twiki page for candidate event ' + eventid) 
        #  f.writelines(entry)
        #  f.close()
        #  os.chdir(twikiroot)
        #  command='echo "initial entry" | ci -l ' +eventid+".txt"
        #  os.popen(command)

