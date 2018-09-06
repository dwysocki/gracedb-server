import logging
import os

from django.views.generic.detail import DetailView

from guardian.shortcuts import get_objects_for_user

from core.file_utils import get_file_list
from events.models import EMGroup
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin, PermissionsFilterMixin
from .models import Superevent
from .utils import get_superevent_by_date_id_or_404


# Set up logger
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    ExposeHideMixin, DisplayFarMixin, PermissionsFilterMixin, DetailView):
    """
    Detail view for superevents.
    """
    model = Superevent
    template_name = 'superevents/detail.html'
    filter_permissions = ['superevents.view_superevent']

    def get_queryset(self):
        """Get queryset and preload some related objects"""
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

        # TODO: filter events for user? Not clear what information we want
        # to show to different groups
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

        # Get list of EMGroup names for emo creation form
        context['emgroups'] = EMGroup.objects.all().order_by('name') \
            .values_list('name', flat=True)

        return context


class SupereventFileList(SupereventDetailView):
    """
    List of files associated with a superevent.
    """
    model = Superevent
    template_name = 'superevents/file_list.html'
    filter_permissions = ['superevents.view_superevent']
    log_view_permission = 'superevents.view_log'
    sort_files = True

    def get_context_data(self, **kwargs):
        # We actually don't want the context from the SupereventDetailView or
        # its mixins so we just override it with the base DetailView
        context = DetailView.get_context_data(self, **kwargs)

        # Get list of logs which are viewable by the user
        viewable_logs = get_objects_for_user(self.request.user, 
            self.log_view_permission, self.object.log_set.all())

        # Here we get the list of files
        file_list = get_file_list(viewable_logs, self.object.datadir)
        if self.sort_files:
            file_list = sorted(file_list)

        # Compile the new context data
        context['file_list'] = file_list

        return context
# NOTE: file "detail" or downloads (and associated permissions) are
# handled through the API. Links on the file list page point to the
# API file download page.
