
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from models import Event, Group, EventLog, Labelling, Label
from models import Pipeline, Search
from models import CoincInspiralEvent
from models import MultiBurstEvent
from models import GrbEvent
from models import EMBBEventLog, EMGroup
from alert import issueAlert, issueAlertForLabel, issueAlertForUpdate
from translator import handle_uploaded_data

from utils.vfile import VersionedFile
from view_utils import _saveUploadedFile
from view_utils import eventToDict, eventLogToDict
from permission_utils import assign_default_event_perms

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group as AuthGroup
from guardian.models import GroupObjectPermission

import os
from django.conf import settings

import json
import datetime

def _createEventFromForm(request, form):
    saved = False
    warnings = []
    try:
        group = Group.objects.get(name=form.cleaned_data['group'])
        pipeline = Pipeline.objects.get(name=form.cleaned_data['pipeline'])
        search_name = form.cleaned_data['search']
        if search_name:
            search = Search.objects.get(name=form.cleaned_data['search'])
        else:
            search = None
        # Create Event
        if pipeline.name in ['gstlal', 'gstlal-spiir', 'MBTAOnline']:
            event = CoincInspiralEvent()
        elif pipeline.name in ['Fermi', 'Swift', 'SNEWS']:
            event = GrbEvent()
        elif pipeline.name in ['CWB', 'CWB2G']:
            event = MultiBurstEvent() 
        else:
            event = Event()

        event.submitter = request.user
        event.group = group
        event.pipeline = pipeline
        event.search = search
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

        event.refresh_perms()

        # Write the event data file to disk. 
        eventDir = event.datadir()
        os.makedirs( eventDir )
        f = request.FILES['eventFile']
        uploadDestination = os.path.join(eventDir, f.name)
        fdest = VersionedFile(uploadDestination, 'w')
        for chunk in f.chunks():
            fdest.write(chunk)
        fdest.close()
        # Create WIKI page

        # Extract Info from uploaded data
        # Temp (ha!) hack to deal with
        # out of band data from Omega to LUMIN.
        try:
            temp_data_loc, translator_warnings  = handle_uploaded_data(event, uploadDestination)
            warnings += translator_warnings
            try:
                # Send an alert.
                # XXX This reverse will give the web-interface URL, not the REST URL.
                # This could be a problem if anybody ever tries to use it.
                issueAlert(event,
                           request.build_absolute_uri(reverse("file", args=[event.graceid(),f.name])),
                           request.build_absolute_uri(reverse("view", args=[event.graceid()])),
                           eventToDict(event, request=request))
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

def create_label(event, labelName, creator, doAlert=True, doXMPP=True):
    d = {}
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
            issueAlertForUpdate(event, description+comment, doxmpp=True, 
                filename=uploadedFile.name,
                serialized_object=eventLogToDict(logEntry, request=request))
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


# 
# A utility to be used with the gracedb.views.view to determine whether 
# there should be a button to control LV-EM access to an event.
# Normally, this button should only be there for people have 'executive'
# level privileges.
# 
# This function returns a tuple: (can_expose, can_protect)
# 
# First, we need to find out whether LV-EM permissions already exist
# for this event. If so, and if the user has permission to revoke them,
# we set can_protect to true.
# 
# OTOH, if the permissions don't already exist, and if the user has
# permission to create them, then we return can_expose=True. 
#
def get_lvem_perm_status(request, event):
    # Figure out the perm status of this event. Is it open to the LV-EM
    # group or not? If so, does the user have permission to revoke permissions?
    # Or if not, can the user add permissions?

    # Get the group
    # Returns a tuple: (can_expose, can_protect)
    try:
        lv_em_group = AuthGroup.objects.get(name__contains='LV-EM')
    except:
        # Something is really wrong.
        return (None, None)

    # Get the content type
    model_name = event.__class__.__name__.lower()
    ctype = ContentType.objects.get(app_label='gracedb', model=model_name)
    
    # Get the permission objects
    try:
        view   = Permission.objects.get(codename='view_%s'   % model_name)
        change = Permission.objects.get(codename='change_%s' % model_name)
    except: 
        # Something is very wrong
        return (None, None)

    # Look for the GroupObjectPermissions
    try:
        lv_em_view = GroupObjectPermission.objects.get(content_type=ctype, 
            object_pk=event.id, group=lv_em_group, permission=view)             
    except:
        lv_em_view = None
    try:
        lv_em_change = GroupObjectPermission.objects.get(content_type=ctype, 
            object_pk=event.id, group=lv_em_group, permission=change)             
    except:
        lv_em_change = None

    if lv_em_view and lv_em_change and \
        request.user.has_perm('guardian.delete_groupobjectpermission'):
        return (False, True)
    elif not lv_em_view and not lv_em_change and \
        request.user.has_perm('guardian.add_groupobjectpermission'):
        return (True, False)
    else:
        return (False, False)

#
# Create an EMBB event log message
#
def create_eel(d, event, user):    
    # create a log entry
    eel = EMBBEventLog(event=event)
    eel.event = event
    eel.submitter = user
    # Assign a group name
    try:
        eel.group = EMGroup.objects.get(name=d.get('group'))
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
    eel.raList = d.get('raList', '')
    eel.raWidthList = d.get('raWidthList', '')

    eel.decList = d.get('decList', '')
    eel.decWidthList = d.get('decWidthList', '')

    eel.gpstimeList = d.get('gpstimeList', '')
    eel.durationList = d.get('durationList', '')

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

    eel.validateMakeRects()
    eel.save()
    return eel
