from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_POST, require_GET
from django.views.generic.detail import DetailView
from django.contrib.auth.models import Group as AuthGroup, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from guardian.models import GroupObjectPermission

from .forms import LogCreateForm, SignoffForm
from .mixins import LvemPermissionMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin
from .models import Superevent, Log
from .utils import get_superevent_by_date_id_or_404, \
    confirm_superevent_as_gw, delete_signoff_for_superevent

from core.http import check_and_serve_file
from core.vfile import VersionedFile
from events.models import EMGroup
from events.mixins import DisplayFarMixin
from events.permission_utils import internal_user_required, is_external

import os
import logging
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    LvemPermissionMixin, DetailView, DisplayFarMixin):
    model = Superevent
    template_name = 'superevents/detail.html'

    # TODO:
    # May want to override this to select superevents by user
    def get_queryset(self):
        qs = super(SupereventDetailView, self).get_queryset()

        # Do some optimization
        qs = qs.select_related('preferred_event__group',
            'preferred_event__pipeline', 'preferred_event__search')
        qs = qs.prefetch_related('labelling_set', 'events')

        return qs

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        superevent_id = self.kwargs.get('superevent_id')
        obj = get_superevent_by_date_id_or_404(self.request, superevent_id,
            queryset)
        return obj

    def get_context_data(self, **kwargs):
        # Get base context
        context = super(SupereventDetailView, self).get_context_data(**kwargs)

        # Add a bunch of extra stuff
        superevent = self.object
        context['preferred_event'] = superevent.preferred_event
        context['preferred_event_labelling'] = superevent.preferred_event \
            .labelling_set.prefetch_related('label', 'creator').all()

        # TODO: can we optimize this more?
        # TODO: also need to filter events for user
        # Pass event graceids
        context['internal_events'] = superevent.get_internal_events() \
            .order_by('id')
        context['external_events'] = superevent.get_external_events() \
            .order_by('id')

        # Get display FARs for preferred_event
        context.update(zip(
            ['display_far', 'display_far_hr', 'far_is_upper_limit'],
            self.get_display_far(obj=superevent.preferred_event)
            )
        )

        # Form to change GW status (only for authorized users)
        # Only show if superevent is NOT a GW.  Require manual intervention to
        # revert since it will surely mess with automated numbering of date IDs
        if not superevent.is_gw and self.request.user.has_perm(
            'confirm_gw_superevent'):
            context['show_gw_status_form'] = True
        else:
            context['show_gw_status_form'] = False

        # Is the user an external user? (I.e., not part of the LVC?) The
        # template needs to know that in order to decide what pieces of
        # information to show.
        context['user_is_external'] = is_external(self.request.user)

        # Get list of EMGroup names for 
        context['emgroups'] = EMGroup.objects.all().order_by('name') \
            .values_list('name', flat=True)

        return context


# Need to restrict ability to view
def old_webview(request, superevent_id):

    # TODO: any special web displays for template for confirmed GWs?
    # can do this in template by checking superevent.is_gw

    # Get superevent object
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)

    # Get context
    context = {}
    context['superevent'] = superevent
    context['preferred_event'] = superevent.preferred_event

    # Display far
    display_far = superevent.preferred_event.far
    far_is_upper_limit = False
    if display_far and is_external(request.user):
        if display_far < settings.VOEVENT_FAR_FLOOR:
            display_far = settings.VOEVENT_FAR_FLOOR
            far_is_upper_limit = True
    context['display_far'] = display_far
    context['far_is_upper_limit'] = far_is_upper_limit
    display_far_yr = display_far
    if display_far:
        far_yr = display_far * (86400*365.25) # yr^-1
        if (far_yr < 1):
            display_far_yr = "1 per {0:0.5g} years".format(1.0/far_yr)
        else:
            display_far_yr = "{0:0.5g} per year".format(far_yr)
    context['display_far_yr'] = display_far_yr

    # Form to change GW status (only for authorized users)
    # Only show if superevent is NOT a GW.  Require manual intervention to
    # revert since it will surely mess with automated numbering of date IDs
    if not superevent.is_gw and request.user.has_perm('confirm_gw_superevent'):
        context['show_gw_status_form'] = True
    else:
        context['show_gw_status_form'] = False

    # Is the user an external user? (I.e., not part of the LVC?) The template 
    # needs to know that in order to decide what pieces of information to show.
    context['user_is_external'] = is_external(request.user)

    # Pass event graceids
    context['internal_events'] = superevent.get_internal_events().order_by('id')
    context['external_events'] = superevent.get_external_events().order_by('id')

    # Form for log creation
    context['log_create_form'] = LogCreateForm(initial={
        'superevent': superevent.id})

    # Temporary method for getting logs
    context['logs'] = superevent.log_set.select_related('issuer').all()

    

    return render(request, 'superevents/old_view.html', context=context)

# Need to add an auth check for this too
# If we use javascript for this eventually, we will want to enforce
# request.is_ajax()
@require_POST
def web_create_log(request, superevent_id):
    """Webpage-based superevent log message creation"""

    # Set up dict for passing to log creation form ----------------------------
    log_dict = request.POST.copy()
    log_dict['issuer'] = request.user.id

    # Get superevent id from superevent_id
    # Get superevent object
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)
    log_dict['superevent'] = superevent.id

    # TODO:
    # After getting superevent, make sure user has appropriate permissions
    # to operate on it

    # File version stuff
    data_file = request.FILES.get('data_file', None) if request.FILES else None
    filename = getattr(data_file, 'name', None)
    log_dict['filename'] = filename
    log_dict['file_version'] = None # will be updated later, if applicable
    log_dict['data_file'] = data_file

    # Validate with form and create new log object ----------------------------
    form = LogCreateForm(log_dict, request.FILES)

    # If form is valid, create new log object from form data
    if form.is_valid():
        # Create new log object
        obj = form.save()

        # Save data_file, if applicable
        #if data_file:

        #    # TODO: fix this!
        #    filepath = '/home/gracedb/' + filename
        #    #filepath = os.path.join(event.datadir, filename)

        #    fdest = VersionedFile(filepath, 'w')
        #    for chunk in data_file.chunks():
        #        fdest.write(chunk)
        #    fdest.close()

        #    # Ascertain the version assigned to this particular file and update
        #    # the log object
        #    obj.file_version = fdest.version
        #    obj.save()

        # TODO:
        # Attach "analyst_comments" tag - web view only

        # TODO:
        # Send alert

        # TODO:
        # attach external tagname if user is external

    # TODO:
    # Don't have a good way to handle errors in the form at present - since we
    # just redirect, we can't update the form with errors.  We can just call
    # the webview function with extra context, but then the URL is "wrong"


    # Return to superevent page
    return HttpResponseRedirect(reverse('superevents:view',
        args=[superevent_id]))


@require_POST
def confirm_as_gw(request, superevent_id):

    # Check user permissions
    if not request.user.has_perm('confirm_gw_superevent'):
        return HttpResponseForbidden('You do not have permission to perform '
            'this action.')

    # TODO: make sure user has permission to see the superevent
    # need to do some kind of filtering on queryset initially, like in
    # rest_framework. maybe add an optional queryset argument to
    # get_superevent_by_date_id_or_404, and a check that the queryset's model
    # is Superevent

    # Get superevent id from superevent_id
    # Get superevent object
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)

    # Set superevent as gw
    confirm_superevent_as_gw(superevent, request.user)

    # Return to superevent page
    return HttpResponseRedirect(reverse('superevents:view',
        args=[superevent_id]))


# TODO:
# filter files for external users (see how this is done for events)
def file_list(request, superevent_id):
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)
    file_list = superevent.list_files(absolute_paths=False)

    context = {
        'file_list': file_list,
        'title': 'Files for {0}'.format(superevent.superevent_id),
        'superevent_id': superevent.superevent_id,
    }
    return render(request, 'superevents/file_list.html', context=context)


# TODO:
# add permission checking
def file_download(request, superevent_id, filename):

    # Get superevent
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)

    # Construct absolute path to file
    file_path = os.path.join(superevent.datadir, filename)

    # Check file and serve it
    return check_and_serve_file(request, file_path, ResponseClass=HttpResponse)


# TODO: add permission checking
@require_POST
def modify_permissions(request, superevent_id):

    # Get superevent
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)

    # Get info from POST data
    group_name = request.POST.get('group_name', None)
    action = request.POST.get('action', None)

    if not group_name or not action:
        msg = 'Modify_permissons requires both group_name and action in POST.'
        return HttpResponseBadRequest(msg)

    # Get the group
    try:
        group = AuthGroup.objects.get(name=group_name)
    except AuthGroup.DoesNotExist:
        return HttpResponseNotFound('Group not found')

    # Get content type and permissions
    ctype = ContentType.objects.get(app_label='superevents',
        model='superevent')
    p_view = Permission.objects.get(codename='view_superevent')
    p_change = Permission.objects.get(codename='change_superevent')

    # Make sure the user is authorized.
    if action == 'expose':
        # Check permissions
        if not request.user.has_perm('guardian.add_groupobjectpermission'):
            msg = "You aren't authorized to create permission objects."
            return HttpResponseForbidden(msg)

        # Create GOPs
        GroupObjectPermission.objects.get_or_create(content_type=ctype,
            group=group, permission=p_view, object_pk=superevent.id)
        GroupObjectPermission.objects.get_or_create(content_type=ctype,
            group=group, permission=p_change, object_pk=superevent.id)

    elif action == 'protect':
        # Check permissions
        if not request.user.has_perm('guardian.delete_groupobjectpermission'):
            msg = "You aren't authorized to delete permission objects."
            return HttpResponseForbidden(msg)

        # Delete gops
        try:
            gop = GroupObjectPermission.objects.get(content_type=ctype,
                group=group, permission=p_view, object_pk=superevent.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass
        try:
            gop = GroupObjectPermission.objects.get(content_type=ctype,
                group=group, permission=p_change, object_pk=superevent.id)
            gop.delete()
        except GroupObjectPermission.DoesNotExist:
            # Couldn't find it. Take no action.
            pass

    else:
        msg = "Unknown action. Choices are 'expose' and 'protect'."
        return HttpResponseBadRequest(msg)

    # Redirect to original page, or home (if original page not found)
    original_url = request.META.get('HTTP_REFERER', reverse('home'))

    return HttpResponseRedirect(original_url)

@require_POST
def modify_signoff(request, superevent_id):
    # Redirect to original page, or home (if original page not found)
    original_url = request.META.get('HTTP_REFERER', reverse('home'))


    # TODO:
    # CHECK IF USER IS AUTHORIZED!!!


    # Set up dict for passing to signoff form
    signoff_dict = request.POST.copy()
    signoff_dict['submitter'] = request.user.id

    # Get superevent id from date-based superevent_id
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)
    signoff_dict['superevent'] = superevent.id
    # TODO:
    # After getting superevent, make sure user has appropriate permissions
    # to operate on it

    # Get action and delete status
    action = signoff_dict.get('action', None)
    delete = signoff_dict.get('delete', None)

    # Use information in signoff_dict to check if a signoff already exists.
    signoff = superevent.signoff_set.filter(
        instrument=signoff_dict['instrument'],
        signoff_type=signoff_dict['signoff_type']).first()

    # Error checking - use messages
    error_msg = None
    if action is None:
        error_msg = "form action not found."
    elif signoff is not None and action == 'CR':
        error_msg = "a signoff already exists, please refresh the page."
    elif signoff is None and action == 'UP':
        error_msg = "signoff no longer exists, please refresh the page."
    elif action == 'create' and delete is True:
        error_msg = "can't delete signoff with creation form."
    if error_msg is not None:
        error_msg = "Error: " + error_msg
        messages.error(request, error_msg)
        return HttpResponseRedirect(original_url)

    # Check for delete parameter.  If True, just delete the signoff.
    if delete:
        delete_signoff_for_superevent(signoff, request.user,
            add_log_message=True, issue_alert=True)
        messages.info(request, "Signoff deleted.")
        return HttpResponseRedirect(original_url)

    # If so, get an update form
    if signoff is not None:
        form = SignoffForm(signoff_dict, instance=signoff)
    else:
        form = SignoffForm(signoff_dict)

    # Validate with form and create new log object ----------------------------

    # If form is valid, create new log object from form data
    error_msg = None
    if form.is_valid():
        # Create/update signoff object
        # Note that form.save() includes creating a log message and
        # generating an alert
        try:
            obj = form.save()
        except Exception as e:
            error_msg = "Error saving signoff: {e}".format(e=e)
        else:
            if action == 'CR':
                messages.info(request, 'Signoff created.')
            elif action == 'UP':
                messages.info(request, 'Signoff updated.')

    else:
        # Send form errors to messaging
        error_msg = "Invalid input: {e}".format(e=form.errors)

    if error_msg is not None:
        logger.error(error_msg)
        messages.error(request, error_msg)

    return HttpResponseRedirect(original_url)

