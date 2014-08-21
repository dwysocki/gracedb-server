from django.db.models import Q
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group

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
