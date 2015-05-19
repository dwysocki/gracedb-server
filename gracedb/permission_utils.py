from django.db.models import Q
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group
from django.utils.functional import wraps
from django.http import HttpResponseForbidden
from gracedb.models import Event

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
    executives = Group.objects.get(name='executives')
    internal   = Group.objects.get(name='Communities:LSCVirgoLIGOGroupMembers')

    # Need to find the *type* of event. Could be a subclass.
    model = event.__class__
    model_name = model.__name__.lower()
    view_codename = 'view_%s' % model_name
    change_codename = 'change_%s' % model_name

    # Assign the permissions
    for g in [executives, internal]:
        assign_perm(view_codename, g, event)
        assign_perm(change_codename, g, event)

#-------------------------------------------------------------------------------
# A wrapper for views that checks whether the user is internal, and if not
# returns a 403.
#-------------------------------------------------------------------------------
def internal_user_required(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        # XXX Should probably move this list of internal groups into settings.
        internal_groups = Group.objects.filter(
            name__in=['Communities:LSCVirgoLIGOGroupMembers', 'executives'])
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
        lvem_groups = [Group.objects.get(name='gw-astronomy:LV-EM')]
        if not set(list(lvem_groups)) & set(list(request.user.groups.all())):
            return HttpResponseForbidden("Forbidden")
        return view(request, *args, **kwargs)
    return inner
