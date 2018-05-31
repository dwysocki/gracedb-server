from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_POST, require_GET

from .models import Superevent, Log
from .forms import LogCreateForm
from .utils import get_superevent_by_date_id_or_404, confirm_superevent_as_gw

from core.http import check_and_serve_file
from core.vfile import VersionedFile
from events.permission_utils import internal_user_required, is_external

import os
import logging
logger = logging.getLogger(__name__)


# Need to restrict ability to view
def webview(request, superevent_id):

    # TODO: any special web displays for template for confirmed GWs?
    # can do this in template by checking superevent.is_gw

    # Get superevent object
    superevent = get_superevent_by_date_id_or_404(request, superevent_id)

    # Get context
    context = {}
    context['superevent'] = superevent
    context['preferred_event'] = superevent.preferred_event

    # Display far
    if superevent.preferred_event is not None:
        display_far = superevent.preferred_event.far
    else:
        display_far = None
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

    return render(request, 'superevents/view.html', context=context)

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
