import logging
import os

from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.views.generic.detail import DetailView

from core.http import check_and_serve_file
from events.models import EMGroup
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin
from .models import Superevent
from .utils import get_superevent_by_date_id_or_404


# Set up logger
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    ExposeHideMixin, DetailView, DisplayFarMixin):
    """
    Detail view for superevents.
    """
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
        obj = get_superevent_by_date_id_or_404(superevent_id, queryset)
        return obj

    def get_context_data(self, **kwargs):
        # Get base context
        context = super(SupereventDetailView, self).get_context_data(**kwargs)

        # Add a bunch of extra stuff
        superevent = self.object
        context['preferred_event'] = superevent.preferred_event
        context['preferred_event_labelling'] = superevent.preferred_event \
            .labelling_set.prefetch_related('label', 'creator').all()

        # TODO: filter events for user (?)
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


# TODO:
# filter files for external users (see how this is done for events)
def file_list(request, superevent_id):
    # TODO: add queryset to args
    superevent = get_superevent_by_date_id_or_404(superevent_id)
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

    # TODO: add queryset to args
    # Get superevent
    superevent = get_superevent_by_date_id_or_404(superevent_id)

    # Construct absolute path to file
    file_path = os.path.join(superevent.datadir, filename)

    # Check file and serve it
    return check_and_serve_file(request, file_path, ResponseClass=HttpResponse)
