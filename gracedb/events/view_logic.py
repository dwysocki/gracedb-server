
from django.http import HttpResponse
from django.urls import reverse
from .models import Event, Group, EventLog, Labelling, Label
from .models import Pipeline, Search
from .models import CoincInspiralEvent
from .models import MultiBurstEvent
from .models import GrbEvent
from .models import SimInspiralEvent
from .models import LalInferenceBurstEvent
from .models import EMBBEventLog, EMGroup
from .models import EMObservation, EMFootprint
from .translator import handle_uploaded_data
from .view_utils import _saveUploadedFile
from .view_utils import eventToDict, eventLogToDict, emObservationToDict, \
    labelToDict
from .permission_utils import assign_default_event_perms

from alerts.events.utils import EventAlertIssuer, EventLabelAlertIssuer, \
    EventEMObservationAlertIssuer, EventEMBBEventLogAlertIssuer
from core.vfile import VersionedFile

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group as AuthGroup
from django.conf import settings
from guardian.models import GroupObjectPermission

import os
import six

import json
import datetime
#import dateutil
from dateutil import parser
from django.utils import timezone
import logging
import pytz
import re

logger = logging.getLogger(__name__)

def _createEventFromForm(request, form):
    saved = False
    warnings = []
    try:
        group = Group.objects.get(name=form.cleaned_data['group'])
        pipeline = Pipeline.objects.get(name=form.cleaned_data['pipeline'])
        search_name = form.cleaned_data['search']
        label_list = form.cleaned_data['labels']
        offline = form.cleaned_data['offline']
        if search_name:
            search = Search.objects.get(name=form.cleaned_data['search'])
        else:
            search = None
        # Create Event
        if pipeline.name in ['gstlal', 'spiir', 'MBTAOnline', 'pycbc',]:
            event = CoincInspiralEvent()
        elif pipeline.name in ['Fermi', 'Swift', 'SNEWS']:
            event = GrbEvent()
        elif pipeline.name in ['CWB', 'CWB2G']:
            event = MultiBurstEvent() 
        elif pipeline.name in ['HardwareInjection',]:
            event = SimInspiralEvent()
        elif pipeline.name in ['oLIB',]:
            event = LalInferenceBurstEvent()
        else:
            event = Event()

        event.submitter = request.user
        event.group = group
        event.pipeline = pipeline
        event.search = search
        event.offline = offline

        # If the event is an injection, look for certain attributes in the POST data.
        # These attributes are unfortunately not found in the SimInspiralTable
        if pipeline.name in ['HardwareInjection',]:
            event.source_channel = request.POST.get('source_channel', None)
            event.destination_channel = request.POST.get('destination_channel', None)
            event.instruments = request.POST.get('instrument', None)

        #  ARGH.  We don't get a graceid until we save,
        #  but we don't know in advance if we can actually
        #  create all the things we need for success!
        #  What to do?!
        event.save()
        saved = True  # in case we have to undo this.
        # Create permissions objects for the new event
        assign_default_event_perms(event)
 
        # XXX In case this is a subclass, let's check and assign default
        # perms on the underlying Event as well.
        if not type(event) is Event:
            underlying_event = Event.objects.get(id=event.id)
            assign_default_event_perms(underlying_event)
            underlying_event.refresh_perms()

        event.refresh_perms()

        # Create data directory/directories
        #    Save uploaded file.
        # Write the event data file to disk. 

        # But there are way too many hardware injections to save them to disk

        f = request.FILES['eventFile']
        if pipeline.name not in ['HardwareInjection',]:
            eventDir = event.datadir
            os.makedirs( eventDir )
            uploadDestination = os.path.join(eventDir, f.name)
            fdest = VersionedFile(uploadDestination, 'w')
            for chunk in f.chunks():
                fdest.write(chunk)
            fdest.close()
            file_contents = None
        else:
            uploadDestination = None
            file_contents = f.read()
        # Create WIKI page

        # Extract Info from uploaded data
        # Temp (ha!) hack to deal with
        # out of band data from Omega to LUMIN.
        try:
            temp_data_loc, translator_warnings  = handle_uploaded_data(event, uploadDestination, 
                file_contents = file_contents)
            warnings += translator_warnings

            # Refresh event from database to ensure attribute types are
            # properly set.
            event.refresh_from_db()

            # Issue event alert before labels are added
            try:
                # XXX This reverse will give the web-interface URL, not the REST URL.
                # This could be a problem if anybody ever tries to use it.
                EventAlertIssuer(event, alert_type='new').issue_alerts()
            except Exception, e:
                message = "Problem issuing an alert (%s)" % e
                logger.warning(message)
                warnings += [message]

            # Add labels here - need event to have been saved already
            for label in label_list:

                # If event already has this label, don't do anything.
                # Append a warning message.
                if label in event.labels.all():
                    warnings.append("Event {0} already labeled with '{1}'" \
                        .format(event.graceid(), label))
                else:
                    # Otherwise, create label
                    labelling = Labelling(event=event, label=label,
                        creator=event.submitter)
                    labelling.save()
                    # Create log message about label
                    message = "Event created with label: {0}".format(label)
                    log = EventLog(event=event, issuer=event.submitter,
                        comment=message)
                    log.save()
                    # Issue label alerts
                    try:
                        EventLabelAlertIssuer(labelling,
                            alert_type='label_added').issue_alerts()
                    except Exception as e:
                        logger.exception('Problem issuing alert (%s)' % str(e))
                        d['warning'] = "Problem issuing alert (%s)" % str(e)

        except Exception, e:
            message = "Problem scanning data. No alert issued (%s)" % e
            logger.warning(message)
            warnings += [message]
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
        message = "Problem creating event (%s)" % e
        logger.warning(message)
        warnings += [message]
        event = None
    return event, warnings

def create_label(event, request, labelName, doAlert=True, doXMPP=True):
    creator = request.user
    event_url = request.build_absolute_uri(reverse('view', args=[event.graceid()]))
    d = {}
    try:
        label = Label.objects.filter(name=labelName)[0]
    except IndexError:
        raise ValueError("No such Label '%s'" % labelName)

    # Don't add a label more than once.
    # track whether label is actually created so as to
    # send the correct HTTP response code
    label_created = False
    if label in event.labels.all():
        d['warning'] = "Event %s already labeled with '%s'" % (event.graceid(), labelName)
    else:
        labelling = Labelling(
                event = event,
                label = label,
                creator = creator
            )
        labelling.save()
        label_created = True
        message = "Label: %s" % label.name
        log = EventLog(event=event, issuer=creator, comment=message)
        try:       
            log.save()
        except Exception as e:
            # XXX This looks a bit odd to me.
            logger.exception('Problem saving log message (%s)' % str(e))
            d['error'] = str(e)

        try:
            EventLabelAlertIssuer(labelling, alert_type='label_added') \
                .issue_alerts()
        except Exception as e:
            logger.exception('Problem issuing alert (%s)' % str(e))
            d['warning'] = "Problem issuing alert (%s)" % str(e)

    # Return warning/error messages (for passing back to client)
    # and label_created bool
    return json.dumps(d), label_created

def delete_label(event, request, labelName, doXMPP=True):
    # This function deletes a label. It starts out a lot like the create
    # label function. First get user and event info:
    creator = request.user
    event_url = request.build_absolute_uri(reverse('view', args=[event.graceid()]))
    d = {}

    # First,throw out an error if the label doesn't exist in the list of available
    # labels.
    try:
        label = Label.objects.filter(name=labelName)[0]
    except IndexError:
        raise ValueError("No such Label '%s'" % labelName)

    # Next, check if the label is in the list of labels for the event. Throw out an
    # error if it isn't. There might be a more elegant way of doing this.
    if label not in event.labels.all():
            d['warning'] = "No label '%s' associated with event %s" % (labelName, event.graceid())
            raise ValueError("No label '%s' associated with event %s" % (labelName, event.graceid()))
    else:
        this_label = Labelling.objects.get(
                event = event,
                label = label,
            )
        this_label.delete()
        message = "Deleted label: %s" % label.name
        log = EventLog(event=event, issuer=creator, comment=message)
        try:
            log.save()
        except Exception as e:
            # XXX This looks a bit odd to me. (<-- retained this message)
            logger.exception('Problem saving log message (%s)' % str(e))
            d['error'] = str(e)

        # send an XMPP alert, no email or phone alerts
        try:
            EventLabelAlertIssuer(this_label, alert_type='label_removed') \
                .issue_alerts()
        except Exception as e:
            logger.exception('Problem issuing alert (%s)' % str(e))
            d['warning'] = "Problem issuing alert (%s)" % str(e)

    # Return the json for some reason. I don't do any alert stuff in here.
    return json.dumps(d)


def get_performance_info():
    # First, try to find the relevant logfile from settings.
    logfilepath = settings.LOGGING['handlers']['performance_file']['filename']
    logfile = open(logfilepath, "r")
   
    # Lookback time is 3 days. These are in UTC.
    dt_now = timezone.now()
    dt_min = dt_now + datetime.timedelta(days=-3)
    
    # Convert to local time
    SERVER_TZ = pytz.timezone(settings.TIME_ZONE)
    dt_now = dt_now.astimezone(SERVER_TZ)
    dt_min = dt_min.astimezone(SERVER_TZ)

    totals_by_status = {}
    totals_by_method = {}

    for line in logfile:
        try:
            match = re.search(r'^(.*) \| (\w+): (\d+): (\S+)$', line)
            datestring, method, status, username = match.groups()
        except:
            continue

        # Check the date to see whether it's fresh enough
        dt = datetime.datetime.strptime(datestring, settings.LOG_DATEFMT)
        # Localize so we can compare with aware datetimes
        dt = SERVER_TZ.localize(dt)
        if dt > dt_min:
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
# A utility to be used with the events.views.view to determine whether 
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
        lv_em_group = AuthGroup.objects.get(name=settings.LVEM_OBSERVERS_GROUP)
    except:
        # Something is really wrong.
        return (None, None)

    # Get the content type
    model_name = event.__class__.__name__.lower()
    ctype = ContentType.objects.get(app_label='events', model=model_name)
    
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

    # Issue alert
    EventEMBBEventLogAlertIssuer(eel, alert_type='embb_event_log') \
        .issue_alerts()

    return eel

#
# Create an EMBB Observaton Record
#
def create_emobservation(request, event):
    d = getattr(request, 'data', None)
    if not d:
        d = getattr(request, 'POST', None)
    # Still haven't got the data?
    if not d:
        raise ValueError('create_emobservation: got no post data from the request.')

    user = request.user

    # create a log entry
    emo = EMObservation(event=event)
    emo.event = event
    emo.submitter = user
    # Assign a group name
    try:
        emo.group = EMGroup.objects.get(name=d.get('group'))
    except:
        raise ValueError('Please specify an EM followup MOU group')

# XXX I have literally no idea why this is necessary.
#    emo.comment = d.get('comment', '')
    comment = d.get('comment', None)
    if not comment:
        comment = ''
    emo.comment = comment

    # Assign RA and Dec, plus widths
    try:
        raList = d.get('ra_list')
        raWidthList = d.get('ra_width_list')

        decList = d.get('dec_list')
        decWidthList = d.get('dec_width_list')

        startTimeList = d.get('start_time_list')
        durationList = d.get('duration_list')
    except Exception, e:
        raise ValueError('Lacking input: %s' % str(e))

    # Handle case where comma-separated strings are submitted rather than lists
    if isinstance(raList, six.string_types):
        raList = map(lambda x: float(x.strip()), raList.split(','))
    if isinstance(raWidthList, six.string_types):
        raWidthList = map(lambda x: float(x.strip()), raWidthList.split(','))
    if isinstance(decList, six.string_types):
        decList = map(lambda x: float(x.strip()), decList.split(','))
    if isinstance(decWidthList, six.string_types):
        decWidthList = map(lambda x: float(x.strip()), decWidthList.split(','))
    if isinstance(startTimeList, six.string_types):
        startTimeList = map(lambda x: x.strip(), startTimeList.split(','))
    if isinstance(durationList, six.string_types):
        durationList = map(lambda x: int(x.strip()), durationList.split(','))

    all_lists = (raList, raWidthList, decList, decWidthList, startTimeList,
        durationList)
    for sub_list in all_lists:
        if len(sub_list) == 0:
            raise ValueError('All fields are required, please try again.')

    # Check all list lengths
    list_length = len(all_lists[0])
    if not all(map(lambda l: len(l) == list_length, all_lists)):
        raise ValueError('ra_list, dec_list, ra_width_list, dec_width_list, '
            'start_time_list, and duration_list must be the same length.')

    # now that we've validated the input, save the emo object
    # Must do this so as to have an id.
    emo.save()

    nList = len(raList)
    for i in range(nList):
        try:
            ra = float(raList[i])
        except:
            raise ValueError('Cannot read RA list element %d of %s'%(i, raList))
        try:
            dec = float(decList[i])
        except:
            raise ValueError('Cannot read Dec list element %d of %s'%(i, decList))
        try:
            start_time = startTimeList[i]
        except:
            raise ValueError('Cannot read GPStime list element %d of %s'%(i, startTimeList))

        try:
            raWidth = float(raWidthList[i])
        except:
            raise ValueError('Cannot read raWidth list element %d of %s'%(i, raWidthList))

        try:
            decWidth = float(decWidthList[i])
        except:
            raise ValueError('Cannot read decWidth list element %d of %s'%(i, decWidthList))

        try:
            duration = int(durationList[i])
        except:
            raise ValueError('Cannot read duration list element %d of %s'%(i, durationList))

        try:
            start_time = parser.parse(start_time)
            if not start_time.tzinfo:
                start_time = pytz.utc.localize(start_time)
        except:
            raise ValueError('Could not parse start time list element %d of %s'%(i, startTimeRealList))

        # Create footprint object 
        EMFootprint.objects.create(observation=emo, ra=ra, dec=dec, 
            raWidth=raWidth, decWidth=decWidth, start_time=start_time, 
            exposure_time=duration)

    # Calculate covering region for observation
    emo.calculateCoveringRegion()
    emo.save()

    # Try issuing an alert.
    try:
        description = "New EMBB observation record for {group}".format(
            group=emo.group)
        EventEMObservationAlertIssuer(emo, alert_type='emobservation') \
            .issue_alerts()
    except Exception, e:
        # XXX Should probably send back warnings, as in the other cases.
        logger.error('error sending alert for emobservation: {0}'.format(e))

    # Write a log message
    log = EventLog.objects.create(issuer=user, comment=description, event=event)

    return emo
    
