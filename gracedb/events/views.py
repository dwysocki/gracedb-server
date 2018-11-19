
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest, Http404
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.template import RequestContext
from django.urls import reverse
from django.shortcuts import render

from core.file_utils import get_file_list
from core.http import check_and_serve_file
from .models import Event, Group, EventLog, Label, Tag, Pipeline, Search, GrbEvent
from .models import EMGroup, Signoff
from .forms import CreateEventForm, SignoffForm

from django.contrib.auth.models import User, Permission
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from .permission_utils import filter_events_for_user, user_has_perm
from .permission_utils import internal_user_required, is_external, \
    check_external_file_access
from guardian.models import GroupObjectPermission

from .view_logic import _createEventFromForm
from .view_logic import get_performance_info
from .view_logic import get_lvem_perm_status
from .view_logic import create_eel
from .view_logic import create_emobservation
from .view_logic import create_label, delete_label
from .view_utils import get_file
from .view_utils import get_recent_events_string
from .view_utils import eventLogToDict
from .view_utils import signoffToDict
from alerts.events.utils import EventAlertIssuer, EventLogAlertIssuer, \
    EventSignoffAlertIssuer, EventVOEventAlertIssuer, \
    EventPermissionsAlertIssuer
from superevents.models import Superevent

# Set up logging
import logging
log = logging.getLogger(__name__)

import os
from django.conf import settings

from .buildVOEvent import buildVOEvent, VOEventBuilderException
from core.vfile import VersionedFile

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

import datetime, pytz
import json
from django.utils.functional import wraps

# 
# for checking queries in the evnet that the user is external
#
from .view_utils import BadFARRange, check_query_far_range

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
    #assert request.user
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

        # Get full list of non-Test events with **OPS label
        events = Event.objects.filter(labelling__label__name=label_name) \
            .exclude(group__name='Test')

        # Split into groups more recent than 1 day and older than 1 day
        one_day_ago = datetime.datetime.utcnow().replace(
            tzinfo=pytz.utc) - datetime.timedelta(days=1)
        new_events = events.filter(created__gte=one_day_ago)
        older_events = events.filter(created__lt=one_day_ago)

        # Put into context dict for template rendering
        context['new_signoff_graceids'] = [e.graceid for e in new_events]
        context['older_signoff_graceids'] = [e.graceid for e in older_events]

        # TODO: ensure not test or MDC types once those are implemented
        # Superevent signoffs
        context['signoff_superevent_ids'] = [s.superevent_id for s in
            Superevent.objects.filter(labelling__label__name=label_name)]

    recent_events = '' 
    if request.user and not is_external(request.user) and settings.SHOW_RECENT_EVENTS_ON_HOME:
        try:
            recent_events = get_recent_events_string(request)
        except Exception, e:
            pass
    context['recent_events'] = recent_events
    
    return render(request, 'gracedb/index.html', context=context)

@internal_user_required
def create(request):
    d = _create(request)
    if isinstance(d, HttpResponse):
        return d
    else:
        return render(request, 'gracedb/create.html', context=d)

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
            # Alert is issued in this function
            event, warnings = _createEventFromForm(request, form)
            if not event:
                # problem creating event...  XXX need an error page for this.
                raise Exception("\n".join(warnings))

            return HttpResponseRedirect(reverse(view, args=[event.graceid]))
        else:
            rv['form'] = form
    return rv

@event_and_auth_required
def logentry(request, event, num=None):
    """Creates an EventLog from the web interface"""

    if request.method == "POST":
        # create a log entry
        elog = EventLog(event=event, issuer=request.user)
        elog.comment = request.POST.get('comment') or request.GET.get('comment')
        uploadedFile = request.FILES.get('uploadedFile', None) if request.FILES else None
        filename = None
        file_version = None
        if uploadedFile:
            filename = uploadedFile.name
            filepath = os.path.join(event.datadir, filename)

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

            tag.event_logs.add(elog)
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
                tag = Tag(name=settings.EXTERNAL_ACCESS_TAGNAME)
                tag.save()
            # I'm putting this in a try/except in case the user has already
            # added the external access tagname somehow, and the following 
            # would result in an IntegrityError
            try:
                tag.event_logs.add(elog)
            except:
                pass

        # Send XMPP alert message
        try:
            if uploadedFile:
                desc = "UPLOAD: '{0}' ".format(uploadedFile.name)
                fname = uploadedFile.name
            else:
                desc = "LOG: "
                fname = ""
            EventLogAlertIssuer(elog, alert_type='log').issue_alerts()
        except Exception as e:
            log.error('Error issuing alert: %s' % str(e))
            return HttpResponse("Failed to send alert for log message: %s" \
                .format(e))

    elif request.method == "GET":
        if not user_has_perm(request.user, 'view', event):
            return HttpResponseForbidden("Forbidden")
        try:
            elog = event.eventlog_set.filter(N=num)[0]
        except Exception, e:
            raise Http404
        
        # Check authorization for this log message
        if is_external(request.user):
            tagnames = [t.name for t in elog.tags.all()]
            if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
                msg = "You do not have permission to view this log message."
                return HttpResponseForbidden(msg)
    else:
        return HttpResponseBadRequest

    if not request.is_ajax():
        return HttpResponseRedirect(reverse('view', args=[event.graceid]))

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
    return render(request, 'gracedb/neighbors_frag.html', context=context)

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
        context['can_modify_t90'] = request.user.has_perm('events.t90_grbevent')

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

    # Calculate easy-to-understand FAR for display purposes.
    # Display as 1 per X years if X > 1 or 1/X per year if X <= 1.
    display_far_yr = display_far
    # Make sure far is not None (handle case of External events)
    if display_far:
        far_yr = display_far * (86400*365.25) # yr^-1
        if (far_yr < 1):
            display_far_yr = "1 per {0:0.5g} years".format(1.0/far_yr)
        else:
            display_far_yr = "{0:0.5g} per year".format(far_yr)
    context['display_far_yr'] = display_far_yr

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
        if is_external(request.user):
            templates.insert(0, 'gracedb/event_detail_coinc_ext.html')
        else:
            templates.insert(0, 'gracedb/event_detail_coinc.html')
    elif event.pipeline.name in settings.GRB_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_GRB.html')
    elif event.pipeline.name.startswith('CWB'):
        templates.insert(0, 'gracedb/event_detail_CWB.html')
    elif event.pipeline.name in ['HardwareInjection',]:
        templates.insert(0, 'gracedb/event_detail_injection.html')
    elif event.pipeline.name in ['oLIB',]:
        templates.insert(0, 'gracedb/event_detail_oLIB.html')

    return render(request, templates, context=context)


#-----------------------------------------------------------------------------------
# For tags.  A new view function.  We need this because the API one would want users
# to have certs stored in their browser.
# XXX Get rid of this and use api views instead?
#-----------------------------------------------------------------------------------

@event_and_auth_required
def taglogentry(request, event, num, tagname):
    # Note: this code is intertwined with the javascript in
    # gracedb/templates/gracedb/event_detail_script.js,
    # specifically lines 461-575, as of 2017/02/28.

    # Boot out unauthenticated users right away
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Forbidden')

    # Get relevant log entry
    eventlog = event.eventlog_set.filter(N=num)[0]

    # Handle access for LV-EM users - if log is not tagged with 'lvem', they
    # shouldn't be able to see it or interact with it.
    if is_external(request.user):
        log_exposed = eventlog.tags.filter(
            name=settings.EXTERNAL_ACCESS_TAGNAME).exists()
        if not log_exposed:
            return HttpResponseForbidden('Forbidden')

    if request.method == "POST":
        # Handle cases where a user leaves the tagname blank.
        if not tagname:
            return HttpResponseBadRequest("Must specify a tagname.")

        # Check authorization - not allowed to touch 'lvem' tag on other
        # users' entries. May want to restrict this more in the future.
        if (is_external(request.user) and
            tagname == settings.EXTERNAL_ACCESS_TAGNAME):
            if request.user != eventlog.issuer:
                msg = "You do not have permission to add or remove this tag."
                return HttpResponseForbidden(msg)

        # Check if tag is already applied to this log entry.
        tag_matches = eventlog.tags.filter(name=tagname)
        if tag_matches:
            msg = "Log already has tag %s." % tagname
            return HttpResponse(msg, content_type="text")

        # Check if tag already exists in the database. If not, create it.
        db_tags = Tag.objects.filter(name=tagname)
        if not db_tags:
            displayName = request.POST.get('displayName', None)
            tag = Tag(name=tagname, displayName=displayName)
            tag.save()
        else:
            tag = db_tags[0]

        # Now add the log message to this tag.
        tag.event_logs.add(eventlog)

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
        # STEP 1: Check authorization
        if (is_external(request.user) and
            tagname == settings.EXTERNAL_ACCESS_TAGNAME):
            if request.user != eventlog.issuer:
                msg = "You do not have permission to add or remove this tag."
                return HttpResponseForbidden(msg)
        # Check if tag is applied to this log entry.
        tags = eventlog.tags.filter(name=tagname)
        if tags:
            tag = tags[0]
            tag.event_logs.remove(eventlog)
        else:
            msg = "Attempted to delete tag that doesn't exist."
            return HttpResponseBadRequest(msg)

        # Create a log entry to document the tag deletion.
        msg = "Removed tag %s for message %s." % (tagname, num)
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

    # Hopefully, this will only ever be called from inside a script.  Just in case...
    if not request.is_ajax():
        return HttpResponseRedirect(reverse('view', args=[event.graceid]))

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

    return render(request, 'gracedb/performance.html', context=context)

#
# A view for the list of files associated with an event.
# The idea is to get rid of that horrible /gracedb-files/ url.
#
@event_and_auth_required
def file_list(request, event):
    f = []

    # Filter file list for external users
    if is_external(request.user):
        viewable_logs = event.eventlog_set.filter(
            tags__name=settings.EXTERNAL_ACCESS_TAGNAME)
        f.extend(get_file_list(viewable_logs, event.datadir))
    else:
        for dirname, dirnames, filenames in os.walk(event.datadir):
            f.extend(filenames)
            break

    context = {}
    context['file_list'] = f
    context['title'] = 'Files for %s' % event.graceid 
    context['graceid'] = event.graceid 
        
    return render(request, 'gracedb/event_filelist.html', context=context)


@event_and_auth_required
def file_download(request, event, filename):

    # If the user is external, check for authorization
    if is_external(request.user):
        if not check_external_file_access(event, filename):
            msg = "You do not have permission to view this file."
            return HttpResponseForbidden(msg)

    file_path = os.path.join(event.datadir, filename)
    return check_and_serve_file(request, file_path,
        ResponseClass=HttpResponse)


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
    ctype = ContentType.objects.get(app_label='events', model=model_name)

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

        # Issue alert
        EventPermissionsAlertIssuer(event, alert_type='exposed').issue_alerts()
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
        # Issue alert
        EventPermissionsAlertIssuer(event, alert_type='hidden').issue_alerts()

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
    return HttpResponseRedirect(reverse("view", args=[event.graceid]))


# A view to create embb log entries
@event_and_auth_required
def emobservation_entry(request, event, num=None):
    if request.method == "POST":
        try:
            # Alert is issued in this function
            create_emobservation(request, event)
        except ValueError, e:
            return HttpResponseBadRequest(str(e))
        except Exception, e:
            return HttpResponseServerError(str(e))

        return HttpResponseRedirect(reverse('view', args=[event.graceid]))
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
    if not request.user.has_perm('events.t90_grbevent'):
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
    return HttpResponseRedirect(reverse("view", args=[event.graceid]))


def get_signoff_type(stype):
    for t in Signoff.SIGNOFF_TYPE_CHOICES:
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
                delete_label(event, request, req_label,
                    can_remove_protected=False)

        # Create a new label.
        label_name = label_stem + status
        create_label(event, request, label_name, can_add_protected=True,
            doAlert=False, doXMPP=False)

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
            tag.event_logs.add(logentry)
        except:
            pass

        # Issue an alert.
        EventSignoffAlertIssuer(signoff, alert_type='signoff_created') \
            .issue_alerts()

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

        delete = request.POST.get('delete', None)
        if delete:
            # delete the operator signoff object
            signoff.delete()

            # remove the existing label
            label_name = label_stem + signoff.status
            existing_label = event.labelling_set.get(
                label__name=label_name).label.name
            delete_label(event, request, existing_label,
                can_remove_protected=True)

            # also restore the label
            create_label(event, request, req_label, can_add_protected=False)

            # Create a log message
            msg = "deleted %s signoff status" % signoff_type
            if len(instrument):
                msg += ' for %s' % instrument
            logentry = EventLog.objects.create(event=event, issuer=request.user, comment=msg)

            # XXX Ugh. Hardcoding tagname here.
            # Add a tag to the log message
            try:
                tag = Tag.objects.get(name='em_follow')
                tag.event_logs.add(logentry)
            except:
                pass
            # Issue an alert.
            EventSignoffAlertIssuer(signoff, alert_type='signoff_deleted') \
                .issue_alerts()
        else:
            if status==None:
                msg = "Please select a valid status."
                return HttpResponseBadRequest(msg)

            if signoff.status != status:
                # remove the existing label
                label_name = label_stem + signoff.status
                existing_label = event.labelling_set.get(
                    label__name=label_name).label.name
                delete_label(event, request, existing_label,
                    can_remove_protected=True)
                # Create a new label.
                label_name = label_stem + status
                create_label(event, request, label_name,
                    can_add_protected=True, doAlert=False, doXMPP=False)

            # update the values
            signoff.status = status
            signoff.comment = comment
            signoff.save()
            # Issue an alert.
            EventSignoffAlertIssuer(signoff, alert_type='signoff_updated') \
                .issue_alerts()

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
                tag.event_logs.add(logentry)
            except:
                pass

    # Finished. Redirect back to the event.
    return HttpResponseRedirect(reverse("view", args=[event.graceid]))

