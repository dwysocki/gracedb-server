
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest, Http404
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.template import RequestContext
from django.core.urlresolvers import reverse, get_script_prefix
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.sites.models import Site
from django.utils.html import strip_tags, escape, urlize
from django.utils.safestring import mark_safe

# Upgrade to Django 1.5: No more function-based generic views.
#from django.views.generic.list_detail import object_list
from django.views.generic.list import ListView
from django.contrib.auth.decorators import login_required

from models import Event, Group, EventLog, Labelling, Label, Tag
from models import CoincInspiralEvent
from models import MultiBurstEvent
from models import GrbEvent
from models import SingleInspiral
from models import EMBBEventLog, EMGroup
from forms import CreateEventForm, EventSearchForm, SimpleSearchForm
from alert import issueAlert, issueAlertForLabel, issueAlertForUpdate
from translator import handle_uploaded_data
from query import parseQuery

from django.contrib.auth.models import User

import urllib

from utils.vfile import VersionedFile

import os
import re
from django.core.mail import mail_admins
from django.conf import settings

from templatetags.scientific import scientific

from buildVOEvent import buildVOEvent, submitToSkyalert

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import json
import datetime

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

def skyalert_authorized(request):
    try:
        return u"{0} {1}".format(request.user.first_name, request.user.last_name) in settings.SKYALERT_SUBMITTERS
    except:
        return False

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


def skyalert(request, graceid):
    event = Event.getByGraceid(graceid)
    createLogEntry = True

    if not event.gpstime:
        request.session['flash_msg'] = "No GPS time.  Event not suitable for submission to SkyAlert"
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    if not event.far:
        request.session['flash_msg'] = "No FAR.  Event not suitable for submission to SkyAlert"
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    if not skyalert_authorized(request):
        request.session['flash_msg'] = "You are not authorized for SkyAlert submission"
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    try:
        skyalert_response = submitToSkyalert(event)
    except Exception, e:
        message = "SkyAlert Submission Error"
        skyalert_response = ""
        # XXX umm.  don't we want to know if this email fails silently?
        mail_admins("SkyAlert Submission Error",
                    "Event: %s\nException: %s\n" % (graceid, e),
                    fail_silently=True)

    flashmessage = None
    if skyalert_response.find("Success") >= 0:
        urlpat = re.compile('https?://[^ ]*')
        match = urlpat.search(skyalert_response)
        if match:
            message = "Submitted to Skyalert: %s" % match.group()
            url = match.group()
            flashmessage = 'Submitted to Skyalert: %s' % url
            message = 'Submitted to Skyalert: <a href="%s">%s</a>' % (url,url)
        else:
            message = "SkyAlert submission problem.  Cannot parse SkyAlert response."
            # XXX umm.  don't we want to know if this email fails silently?
            mail_admins("SkyAlert response parsing problem",
                        "Event: %s\nSkyAlert Response: %s\n" % (graceid, skyalert_response),
                        fail_silently=True)
    elif (skyalert_response.find('already') >= 0) or (skyalert_response.find('Duplicate') >= 0):
            message = "Event already submitted to SkyAlert"
            createLogEntry = False
    elif skyalert_response:
        message = "Skyalert Submission Failed."
        mail_admins("SkyAlert submission failed",
                    "Event: %s\nSkyAlert Response: %s\n" % (graceid, skyalert_response),
                    fail_silently=True)

    request.session['flash_msg'] = flashmessage or message

    if createLogEntry:
        logentry = EventLog(event=event, issuer=request.ligouser, comment=message)
        try:
            logentry.save()
        except:
            # XXX Failed to create log entry for skyalert submission.
            # Error message?
            pass

    return HttpResponseRedirect(reverse(view, args=[graceid]))

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

def _createEventFromForm(request, form):
    saved = False
    warnings = []
    try:
        group = Group.objects.filter(name=form.cleaned_data['group'])
        atype = form.cleaned_data['type']
        # Create Event
        if atype in ['LM', 'HM', 'MBTA']:
            event = CoincInspiralEvent()
        elif atype == "GRB":
            event = GrbEvent()
        elif atype == "CWB":
            event = MultiBurstEvent()
        else:
            event = Event()
        event.submitter = request.user
        event.group = group[0]
        event.analysisType = atype
        #  ARGH.  We don't get a graceid until we save,
        #  but we don't know in advance if we can actually
        #  create all the things we need for success!
        #  What to do?!
        event.save()
        saved = True  # in case we have to undo this.
        # Create data directory/directories
        #    Save uploaded file.
        dirPrefix = GRACEDB_DATA_DIR
        eventDir = os.path.join(dirPrefix, event.graceid())
        os.mkdir( eventDir )
        os.mkdir( os.path.join(eventDir,"private") )
        os.mkdir( os.path.join(eventDir,"general") )
        #os.chmod( os.path.join(eventDir,"general"), int("041777",8) )
        os.chmod( os.path.join(eventDir,"general"), 041777 )
        f = request.FILES['eventFile']
        uploadDestination = os.path.join(eventDir, "private", f.name)
        fdest = VersionedFile(uploadDestination, 'w')
        # Save uploaded file into user private area.
        for chunk in f.chunks():
            fdest.write(chunk)
        fdest.close()
        # Create WIKI page

        # Extract Info from uploaded data
        # Temp (ha!) hack to deal with
        # out of band data from Omega to LUMIN.
        try:
            temp_data_loc = handle_uploaded_data(event, uploadDestination)
            try:
                # Send an alert.
                # XXX This reverse will give the web-interface URL, not the REST URL.
                # This could be a problem if anybody ever tries to use it.
                # NOTE: The clusterurl method should be considered deprecated.
                issueAlert(event,
                           #os.path.join(event.clusterurl(), "private", f.name),
                           request.build_absolute_uri(reverse("file", args=[event.graceid(),f.name])),
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
    fname = os.path.join(GRACEDB_DATA_DIR, event.graceid(), "private", uploadedFile.name)
    f = VersionedFile(fname, "w")
    for chunk in uploadedFile.chunks():
        f.write(chunk)
    f.close()
    return f.version

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
                            issuer=request.user,
                            comment=comment)
        if uploadedFile:
            file_version = None
            try:
                file_version = _saveUploadedFile(event, uploadedFile)
                logEntry.filename = uploadedFile.name
                logEntry.file_version = file_version
            except Exception, e:
                rdict['error'] = "Problem saving file: %s" % str(e)
        try:
            logEntry.save()

            description = "LOG: "
            if uploadedFile:
                description = "UPLOAD: '%s' " % uploadedFile.name
            issueAlertForUpdate(event, description+comment, doxmpp=True, filename=uploadedFile.name)
        except Exception, e:
            rdict['error'] = "Failed to save log message: %s" % str(e) 

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
        # XXX Note:  filename or comment oughta have a version
        log = EventLog(event=event,
                       issuer=request.user,
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
            fname = os.path.join(GRACEDB_DATA_DIR, event.graceid(), "private", uploadedfile.name)
            f = VersionedFile(fname, 'w')
            for chunk in uploadedfile.chunks():
                f.write(chunk)
            f.close()
            log.file_version = f.version
            log.save()
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

def create_label(graceid, labelName, creator, doAlert=True, doXMPP=True):

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
                creator = creator
            )
        labelling.save()
        message = "Label: %s" % label.name
        log = EventLog(event=event, issuer=creator, comment=message)
        try:       
            log.save()
        except Exception as e:
            # XXX This looks a bit odd to me.
            d['error'] = str(e)

        try:
            issueAlertForLabel(event, label, doXMPP)
        except Exception, e:
            d['warning'] = "Problem issuing alert (%s)" % str(e)
    # XXX Strange return value.  Just warnings.  Can really be ignored, I think.
    return json.dumps(d)

def cli_label(request):
    graceid = request.POST.get('graceid')
    labelName = request.POST.get('label')

    doxmpp = request.POST.get('alert') == "True"
    d = create_label(graceid, labelName, request.user, doXMPP=doxmpp)

    msg = str(d)
    response = HttpResponse(mimetype='application/json')
    response.write(msg)
    response['Content-length'] = len(msg)

    return response

import html5lib
def sanitize_html(data):
    """

    >>> sanitize_html5lib("foobar<p>adf<i></p>abc</i>")
    u'foobar<p>adf<i></i></p><i>abc</i>'
    >>> sanitize_html5lib('foobar<p style="color:red; remove:me; background-image: url(http://example.com/test.php?query_string=bad);">adf<script>alert("Uhoh!")</script><i></p>abc</i>')
    u'foobar<p style="color: red;">adf&lt;script&gt;alert("Uhoh!")&lt;/script&gt;<i></i></p><i>abc</i>'
    """
    from html5lib import treebuilders, treewalkers, serializer, sanitizer

    p = html5lib.HTMLParser(tokenizer=sanitizer.HTMLSanitizer, tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parseFragment(data)

    walker = treewalkers.getTreeWalker("dom")

    stream = walker(dom_tree)

    s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
    return "".join(s.serialize(stream))


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
        log = EventLog(event=event, issuer=request.user, comment=message)
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
    ack = "(%s/%s) " % (request.META['SERVER_NAME'], settings.CONFIG_NAME)
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
        d =  json.dumps(d)
        response.write(d)
        response['Content-length'] = len(d)
    else:
        # Old client
        response = HttpResponse(mimetype='text/plain')
        response.write(ack)
        response['Content-length'] = len(ack)
    return response

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

import logging

def view(request, graceid):
    logger = logging.getLogger(__name__)
    logger.debug("Hi from inside the view.")
    context = {}
    try:
        a = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        raise Http404
    context['object'] = a
    context['groups'] = [g.name for g in EMGroup.objects.all()]
    context['eventdesc'] = get_file(graceid, "event.log")
    context['userdesc'] = get_file(graceid, "user.log")
    context['nearby'] = [(event.gpstime - a.gpstime, event)
                            for event in a.neighbors()]
    context['skyalert_authorized'] = skyalert_authorized(request)
    context['blessed_tags'] = settings.BLESSED_TAGS
    context['single_inspiral_events'] = list(a.singleinspiral_set.all())
    context['neighbor_delta'] = "[%+d,%+d]" % (-5,5)
    context['SKYMAP_VIEWER_SERVICE_URL'] = settings.SKYMAP_VIEWER_SERVICE_URL

    return render_to_response(
        [ 'gracedb/event_detail_{0}.html'.format(a.analysisType),
          'gracedb/event_detail.html'],
        context,
        context_instance=RequestContext(request))

def cli_search(request):
    assert request.user
    form = SimpleSearchForm(request.POST)
    if form.is_valid():
        objects = form.cleaned_data['query']

        if 'ligolw' in request.POST or 'ligolw' in request.GET:
            from glue.ligolw import utils
            if objects.count() > 1000:
                return HttpResponseBadRequest("Too many events.")
            xmldoc = assembleLigoLw(objects)
            response = HttpResponse(mimetype='application/xml')
            response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
            utils.write_fileobj(xmldoc, response)
            return response

        accessFun = {
            "labels" : lambda e: \
                ",".join([labelling.label.name for labelling in e.labelling_set.all()]),
            "analysisType" : lambda e: e.get_analysisType_display(),
            "gpstime" : lambda e: str(e.gpstime) or "",
            "created" : lambda e: e.created.isoformat(),
            "dataurl" : lambda e: e.weburl(),
            "graceid" : lambda e: e.graceid(),
            "group" : lambda e: e.group.name,
        }
        defaultAccess = lambda e, a: str(getattr(e,a,None) or "")

        defaultColumns = "graceid,labels,group,analysisType,far,gpstime,created,dataurl"
        columns = request.POST.get('columns')
        if not columns:
            columns = defaultColumns
        columns = columns.split(',')

        header = "#" + "\t".join(columns)
        outTable = [header]
        for e in objects:
            row = [ accessFun.get(column, lambda e: defaultAccess(e,column))(e) for column in columns ]
            outTable.append("\t".join(row))
        d = {'output': "\n".join(outTable)}
    else:
        d = {'error': ""}
        for key in form.errors:
            d['error'] += "%s: %s\n" % (key, strip_tags(form.errors[key]))
    response = HttpResponse(mimetype='application/javascript')
    msg = json.dumps(d)
    response['Content-length'] = len(msg)
    response.write(msg)
    return response


def assembleLigoLw(objects):
    from glue.ligolw import ligolw
    # lsctables MUST be loaded before utils.
    from glue.ligolw import lsctables
    from glue.ligolw import utils
    from glue.ligolw.utils import ligolw_add

    xmldoc = ligolw.Document()
    for obj in objects:
        fname = os.path.join(GRACEDB_DATA_DIR, obj.graceid(), "private", "coinc.xml")
        utils.load_filename(fname, xmldoc=xmldoc)

    ligolw_add.reassign_ids(xmldoc)
    ligolw_add.merge_ligolws(xmldoc)
    ligolw_add.merge_compatible_tables(xmldoc)
    return xmldoc

def search(request, format=""):
    if not request.user or not request.user.is_authenticated():
        return HttpResponseForbidden("Forbidden")
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
        msg = json.dumps(d)
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

def timeline(request):
    from utils import gpsToUtc
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
    msg = json.dumps(d)
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
                        " ".join(["""<span onmouseover="tooltip.show(tooltiptext('%s', '%s', '%s'));" onmouseout="tooltip.hide();"  style="color: %s"> %s </span>""" % (label.label.name, label.creator.username, label.created, label.label.defaultColor, label.label.name)
                                for label in object.labelling_set.all()]),
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

                        object.instruments,

                        scientific(object.far),

                        '<a href="%s">Data</a>' % object.weburl(),

                        #created_times['gps'],
                        created_times.get('utc',""),

                        "%s %s" % (object.submitter.first_name, object.submitter.last_name)

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
        msg = json.dumps(d)
    except Exception, e:
        # XXX Not right not right not right.
        msg = "{}"
    response['Content-length'] = len(msg)
    response.write(msg)

    #query = request.POST['query']

    return response

def get_file(graceid, filename="event.log"):
    dirPrefix = GRACEDB_DATA_DIR
    logfilename = os.path.join(dirPrefix, graceid, "private", filename)
    contents = ""
    try:
        lines = open(logfilename, "r").readlines()
        contents = "<br/>".join([ escape(line) for line in lines])
        contents = mark_safe(urlize(contents))
    except Exception, e:
        contents = None
    return contents


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

def get_performance_info():
    # First, try to find the relevant logfile from settings.
    logfilepath = settings.LOGGING['handlers']['performance_file']['filename']
    logfile = open(logfilepath, "r")
   
    # Now parse the log file
    dateformat = '%Y-%m-%dT%H:%M:%S' # ISO format. I think.

    # Lookback time is 3 days.
    dt_now = datetime.datetime.now()
    dt_min = dt_now + datetime.timedelta(days=-3)

    creation_status_totals = {}
    annotation_status_totals = {}
    total_create_requests = 0
    total_annotate_requests = 0

    totals_by_status = {}
    totals_by_method = {}

    for line in logfile:
        datestring = line[0:len('YYYY-MM-DDTHH:MM:SS')]
        # Check the date to see whether it's fresh enough
        dt = datetime.datetime.strptime(datestring, dateformat)
        if dt > dt_min:
            # Get rid of the datestring and the final colon.
            line = line[len(datestring)+1:]
            # Parse
            method, status, username = line.split(':')
            method = method.strip()
            status = int(status.strip())
            username = username.strip()

            if method not in totals_by_method.keys():
                totals_by_method[method] = 1
                totals_by_status[method] = {status: 1}
            else:
                totals_by_method[method] += 1
                if status not in totals_by_status[method].keys():
                    totals_by_status[method][status] = 1
                else:
                    totals_by_status[method][status] += 1

    # Calculate summary information:
    summaries = {}
    for method in totals_by_method.keys():
        summaries[method] = {'gt_500': 0, 'btw_300_500': 0}
        for key in totals_by_status[method].keys():
            if key >= 500:
                summaries[method]['gt_500'] += totals_by_status[method][key]
            elif key >= 300:
                summaries[method]['btw_300_500'] += totals_by_status[method][key]
        # Normalize
        if totals_by_method[method] > 0:
            for key in summaries[method].keys():
                summaries[method][key] = float(summaries[method][key])/totals_by_method[method]

    context = {
            'summaries': summaries,
            'current_time' : str(dt_now),
            'totals_by_status' : totals_by_status,
            'totals_by_method' : totals_by_method,
    }
    return context

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

def create_eel(d, event, user):        
    # create a log entry
    eel = EMBBEventLog(event=event)
    eel.event = event
    eel.submitter = user
    # Assign a group name
    try:
        eel.group = EMGroup.objects.get(shortName=d.get('group'))
    except:
        raise ValueError('Please specify an EM followup MOU group')

    # Assign an instrument name
    eel.instrument = d.get('instrument', '')

    # Assign a group-specific footprint ID (if provided)
    eel.footprintID = d.get('footprintID', '')

    # Assign the EM spectrum string
    try:
        eel.waveband = d.get('waveband')
    except:
        raise ValueError('Please specify a waveband')

    # Assign RA and Dec, plus widths
    eel.ra = d.get('ra', None)
    eel.dec = d.get('dec', None)
    eel.raWidth = d.get('raWidth', None)
    eel.decWidth = d.get('decWidth', None)

    # Assign gpstime and duration.
    eel.gpstime = d.get('gpstime', None)
    eel.duration = d.get('duration', None)

    # Assign EEL status and observation status.
    try:
        eel.eel_status = d.get('eel_status')
    except: 
        raise ValueError('Please specify an EEL status.')
    try:
        eel.obs_status = d.get('obs_status')
    except: 
        raise ValueError('Please specify an observation status.')

    eel.extra_info_dict = d.get('extra_info_dict', '') 
    eel.comment = d.get('comment', '') 
    eel.save()
    return eel

# A view to create embb log entries
def embblogentry(request, graceid, num=None):
    try:
        event = Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        raise Http404
    if request.method == "POST":
        try:
            eel = create_eel(request.POST, event, request.user)
        except ValueError, e:
            return HttpResponseBadRequest(str(e))
        except Exception, e:
            return HttpResponseServerError(str(e))
    else:
        try:
            eel = event.eventlog_set.filter(N=num)[0]
        except Exception:
            raise Http404

    if not request.is_ajax():
        return HttpResponseRedirect(reverse(view, args=[graceid]))

    rv = {}
    rv['comment'] = eel.comment
    rv['submitter'] = eel.issuer.username
    rv['created'] = eel.created.isoformat()

    return HttpResponse(json.dumps(rv), content_type="application/json")
