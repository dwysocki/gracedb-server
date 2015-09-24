from django.conf import settings
from django.db.models import Q
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group
from django.utils.functional import wraps
from django.http import HttpResponseForbidden
from gracedb.models import Event
import os

#-------------------------------------------------------------------------------
# A convenient wrapper for permission checks.
#-------------------------------------------------------------------------------
def user_has_perm(user, shortname, obj):
    codename = shortname + '_%s' % obj.__class__.__name__.lower()
    return user.has_perm(codename, obj)

#-------------------------------------------------------------------------------
# Filter a queryset of Event objects according to user permissions.
# This relies on the storage of perm info on the event itself, and is
# a much faster alternative to guardian.shortcuts.get_objects_for_user
# when there are many objects.
#-------------------------------------------------------------------------------
def filter_events_for_user(events, user, shortname):
    # If user is None, return empty queryset
    if not user:
        return Event.objects.none()
    if not user.groups.count():
        return Event.objects.none()
    if not events:
        return Event.objects.none()
    auth_filter = Q()
    for group in user.groups.all():
        perm_string = '%s_can_%s' % (group.name, shortname)
        auth_filter = auth_filter | Q(perms__contains=perm_string)
    return events.filter(auth_filter)

#-------------------------------------------------------------------------------
# Create default permission objects for an event. This is intended
# to be used upon event creation. By default only internal LVC users
# will be able to view or annotate an event.
#-------------------------------------------------------------------------------
def assign_default_event_perms(event):
    # Retrieve the group objects
    executives = Group.objects.get(name=settings.EXEC_GROUP)
    internal   = Group.objects.get(name=settings.LVC_GROUP)

    # Need to find the *type* of event. Could be a subclass.
    model = event.__class__
    model_name = model.__name__.lower()
    view_codename = 'view_%s' % model_name
    change_codename = 'change_%s' % model_name

    # Assign the permissions
    for g in [executives, internal]:
        assign_perm(view_codename, g, event)
        assign_perm(change_codename, g, event)

    # If the event is an MDC event, then we expose it to LV-EM also
    if event.search and event.search.name == 'MDC':
        lvem = Group.objects.get(name=settings.LVEM_GROUP)
        assign_perm(view_codename, lvem, event)
        assign_perm(change_codename, lvem, event)

#-------------------------------------------------------------------------------
# A wrapper for views that checks whether the user is internal, and if not
# returns a 403.
#-------------------------------------------------------------------------------
def internal_user_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        # XXX Should probably move this list of internal groups into settings.
        internal_groups = Group.objects.filter(
            name__in=[settings.LVC_GROUP, settings.EXEC_GROUP])
        if not set(list(internal_groups)) & set(list(request.user.groups.all())):
            return HttpResponseForbidden("Forbidden")
        return view(request, *args, **kwargs)
    return inner

#-------------------------------------------------------------------------------
# A wrapper for views that checks whether the user is in the LV-EM group, and if not
# returns a 403.
#-------------------------------------------------------------------------------
def lvem_user_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        # XXX Should probably move this list of internal groups into settings.
        lvem_groups = [Group.objects.get(name=settings.LVEM_GROUP)]
        if not set(list(lvem_groups)) & set(list(request.user.groups.all())):
            return HttpResponseForbidden("Forbidden")
        return view(request, *args, **kwargs)
    return inner

#-------------------------------------------------------------------------------
# A utility for determining whether a user is 'external' (i.e., not part of the 
# LVC). This is useful for controlling which pieces of information to display
# in a view.
#-------------------------------------------------------------------------------
def is_external(user):
    if user:
        user_groups = [g.name for g in user.groups.all()]
        if settings.LVC_GROUP not in user_groups:
            return True
        return False
    else:
        return True
#    if user.username == 'branson.stephens@LIGO.ORG':
#        return False
#    return True

#-------------------------------------------------------------------------------
# A utility for determining whether an external user should have access to a 
# particular file, given the event and filename. This is done by finding the
# log message associated with that file and checking that the log message is
# tagged for external access. Returns True if the user should have access, and 
# False if not. Note that this presumes that the user is external and does not
# check this.
#-------------------------------------------------------------------------------
def get_file_version(filename):
    version = None
    base_filename = filename
    if len(filename.split(',')) > 1:
        try:
            toks = filename.split(',')
            base_filename = toks[0]
            version = int(toks[1])
        except:
            pass
    return base_filename, version

def check_external_file_access(event, filename):
    filename, version = get_file_version(filename)
    if version is None:
        # Figure out the version by following the link
        filepath = os.path.join(event.datadir(), filename)
        if os.path.islink(filepath):
            target_file = os.path.realpath(filepath)
            target_basename = os.path.basename(target_file)
            filename, version = get_file_version(target_basename)
        else:
            return False

    # find the associated log message
    logs = event.eventlog_set.filter(filename=filename, file_version=version)
    count = logs.count()
    log = None
    if count == 0:
        # Could not find logfile 
        # XXX Write log
        return False
    elif count > 1:
        # There should only be one file. Ugh. What's going on?
        # XXX Write log 
        return False
    else:
        log = logs[0]

    # check access
    tagnames = [t.name for t in log.tag_set.all()]
    if settings.EXTERNAL_ACCESS_TAGNAME not in tagnames:
        return False
    return True

