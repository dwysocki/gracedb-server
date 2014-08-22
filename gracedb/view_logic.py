
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from models import Event, Group, EventLog, Labelling, Label
from models import CoincInspiralEvent
from models import MultiBurstEvent
from models import GrbEvent
from alert import issueAlert, issueAlertForLabel, issueAlertForUpdate
from translator import handle_uploaded_data

from utils.vfile import VersionedFile
from view_utils import _saveUploadedFile
from permission_utils import assign_default_event_perms

import os
from django.conf import settings

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import json
import datetime

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

        # Create permissions objects for the new event
        assign_default_event_perms(event)
 
        # XXX In case this is a subclass, let's check and assign default
        # perms on the underlying Event as well.
        if not type(event) is Event:
            underlying_event = Event.objects.get(id=event.id)
            assign_default_event_perms(underlying_event)
            underlying_event.refresh_perms()
        else:
            event.refresh_perms()

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

def get_performance_info():
    # First, try to find the relevant logfile from settings.
    logfilepath = settings.LOGGING['handlers']['performance_file']['filename']
    logfile = open(logfilepath, "r")
   
    # Now parse the log file
    dateformat = '%Y-%m-%dT%H:%M:%S' # ISO format. I think.

    # Lookback time is 3 days.
    dt_now = datetime.datetime.now()
    dt_min = dt_now + datetime.timedelta(days=-3)

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


