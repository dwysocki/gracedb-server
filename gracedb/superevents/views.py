import logging
import os
from lal import gpstime

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.detail import DetailView
from django.views.generic import ListView

from guardian.shortcuts import get_objects_for_user

from core.file_utils import get_file_list
from events.models import EMGroup
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from ligoauth.decorators import public_if_public_access_allowed
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin, PermissionsFilterMixin, ConfirmGwFormMixin
from .models import Superevent, VOEvent
from .utils import get_superevent_by_date_id_or_404


# Set up logger
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    ExposeHideMixin, ConfirmGwFormMixin, DisplayFarMixin,
    PermissionsFilterMixin, DetailView):
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

@method_decorator(public_if_public_access_allowed, name='dispatch')
class SupereventPublic(DisplayFarMixin, ListView):
    model = Superevent
    template_name = 'superevents/public_alerts.html'
    filter_permissions = ['superevents.view_superevent']
    log_view_permission = 'superevents.view_log'
    noticeurl_template = 'https://gcn.gsfc.nasa.gov/notices_l/{s_id}.lvc'
    gcnurl_template = 'https://gcn.gsfc.nasa.gov/other/GW{sd_id}.gcn3'
    default_skymap_filename = 'bayestar.png'
    pe_results_tagname = 'pe_results'

    def get_queryset(self, **kwargs):
        # Query only for public events
        # NOTE: may want to fix this to only O3 events at some point
        qs = Superevent.objects.filter(is_exposed=True,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION) \
            .prefetch_related('voevent_set', 'log_set')
        return qs

    def get_skymap_image(self, superevent, voevent=None):
        skymap_image = None
        public_logs = superevent.log_set.filter(tags__name='public')

        # Try to get skymap from latest non-retraction VOEvent
        if voevent is not None and voevent.skymap_filename is not None:
            # Assume filename is the same, with a different suffix.
            voevent_skymap_image = voevent.skymap_filename.replace('fits.gz',
                                                                   'png')
            # See if a public log exists with that filename
            if public_logs.filter(filename=voevent_skymap_image).exists():
                skymap_image = voevent_skymap_image

        # If skymap_image is None, we didn't find an image based on the
        # skymap file in the VOEvent, so try the default.
        if (skymap_image is None and
            public_logs.filter(filename=self.default_skymap_filename).exists()):
            skymap_image = self.default_skymap_filename

        if skymap_image:
            # Add version to image name to be safe
            log = public_logs.filter(filename=skymap_image) \
                .order_by('-file_version').first()
            skymap_image = log.versioned_filename

            skymap_image = reverse(
                'legacy_apiweb:default:superevents:superevent-file-detail',
                args=[superevent.default_superevent_id, skymap_image]
            )
        return skymap_image

    def get_context_data(self, **kwargs):
        # Get base context
        context = super(SupereventPublic, self).get_context_data(**kwargs)

        # For each superevent, get list of log messages and construct pastro
        # string
        candidates = 0
        for se in self.object_list:

            # External links to GCN notice and circular
            se.noticeurl = self.noticeurl_template.format(s_id=
                se.default_superevent_id)
            se.gcnurl = self.gcnurl_template.format(sd_id=
                se.default_superevent_id[1:])

            se.t0_iso = gpstime.gps_to_utc(se.t_0).isoformat(' ').split('.')[0]
            se.t0_utc = se.t0_iso.split()[1]

            # Get display FARs for preferred_event
            se.far_hz, se.far_hr, se.far_limit = self.get_display_far(
                obj=se.preferred_event)

            # Get list of voevents, filtering out retractions
            voe = se.voevent_set.exclude(voevent_type=
                VOEvent.VOEVENT_TYPE_RETRACTION).order_by('-N').first()

            # Get skymap image (if a public one exists)
            se.skymap_image = self.get_skymap_image(se, voe)

            # Was the candidate retracted?
            se.retract = se.voevent_set.filter(voevent_type=
                VOEvent.VOEVENT_TYPE_RETRACTION).exists()
            candidates += int(not se.retract)

            # Get list of viewable logs for user which are tagged with
            # 'analyst_comments'
            viewable_logs = se.log_set.filter(tags__name='public').filter(
                tags__name='analyst_comments')
            # Compile comments from these logs
            se.comments = ' ** '.join(list(viewable_logs.values_list(
                'comment', flat=True)))
            if se.retract:
                if se.comments:
                    se.comments = " ** " + se.comments
                se.comments = "RETRACTED" + se.comments

            # Get list of PE results
            pe_results = get_objects_for_user(self.request.user,
                self.log_view_permission,
                klass=se.log_set.filter(tags__name=self.pe_results_tagname))
            # Compile comments from these logs
            se.pe = ' ** '.join(list(pe_results.values_list(
                'comment', flat=True)))

            # Get p_astro probabilities
            if voe is not None:
                pastro_values = [("BNS", voe.prob_bns),
                    ("NSBH", voe.prob_nsbh),
                    ("BBH", voe.prob_bbh),
                    ("Terrestrial", voe.prob_terrestrial),
                    ("MassGap", voe.prob_mass_gap)]
                pastro_values.sort(reverse=True, key=lambda (a,b): b)
                sourcelist = []
                for key, value in pastro_values:
                    if value > 0.01:
                        prob = int(round(100*value))
                        if prob == 100: prob = '>99'
                        sourcestr = "{0} ({1}%)".format(key, prob)
                        sourcelist.append(sourcestr)
                se.sourcetypes = ', '.join(sourcelist)

        # Number of non-retracted candidate events
        context['candidates'] = candidates

        return context
