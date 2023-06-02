import logging
import os
from lal import gpstime

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.detail import DetailView
from django.views.generic import ListView

from guardian.shortcuts import get_objects_for_user

from core.file_utils import get_file_list
from events.models import EMGroup
from events.models import Label
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from ligoauth.decorators import public_if_public_access_allowed
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin, PermissionsFilterMixin, ConfirmGwFormMixin, \
    RRTViewMixin
from .models import Superevent, VOEvent
from search.constants import RUN_MAP
from .utils import get_superevent_by_date_id_or_404, \
    get_superevent_by_sid_or_gwid_or_404


# Set up logger
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    RRTViewMixin, ExposeHideMixin, ConfirmGwFormMixin, DisplayFarMixin,
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
        obj = get_superevent_by_sid_or_gwid_or_404(superevent_id, queryset)
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

        # TODO: determine what info from pipeline-preferred events gets shown 
        # to the public on the superevent page. For now, just show everything to
        # internal users.

        context['pipeline_preferred_events'] = superevent.pipeline_preferred_events.all()

        # Is the user an external user? (I.e., not part of the LVC?) The
        # template needs to know that in order to decide what pieces of
        # information to show.
        context['user_is_external'] = is_external(self.request.user)

        # Get list of EMGroup names for emo creation form
        context['emgroups'] = EMGroup.objects.all().order_by('name') \
            .values_list('name', flat=True)

        # Get list of Log objects associated with this superevent
        log_set_query_kwargs = {}
        if context['user_is_external']:
            log_set_query_kwargs['tags__name'] = 'public'
        context['log_list'] = superevent.log_set.filter(**log_set_query_kwargs)

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
            self.log_view_permission, klass=self.object.log_set.all())

        file_list = viewable_logs.exclude(filename='').order_by('filename')

        # Here we get the list of files
        #file_list = get_file_list(viewable_logs, self.object.datadir)
        #if self.sort_files:
        #    file_list = sorted(file_list)

        # Compile the new context data
        context['file_list'] = file_list

        # And the superevent datadir
        context['datadir'] = self.object.datadir

        return context

# NOTE: file "detail" or downloads (and associated permissions) are
# handled through the API. Links on the file list page point to the
# API file download page.

# Redirect /superevents/public/<slug>/ to a anchor link on 
# /superevents/public/#<slug> that's nominally tied to a given 
# observation run. If for some reason a user puts in a random 
# slug, then it just goes to the top of the public page, so it's
# pretty fail-safe. 
def public_alerts_redirect(request):
    return redirect('/superevents/public/{run}'.format(
        run=settings.PUBLIC_PAGE_RUNS[0]))

# The public alerts page:
@method_decorator(public_if_public_access_allowed, name='dispatch')
class SupereventPublic(DisplayFarMixin, ListView):
    model = Superevent
    template_name = 'superevents/public_alerts.html'
    filter_permissions = ['superevents.view_superevent']
    log_view_permission = 'superevents.view_log'
    noticeurl_template = 'https://gcn.gsfc.nasa.gov/notices_l/{s_id}.lvc'
    gcnurl_template_o3 = 'https://gcn.gsfc.nasa.gov/other/GW{sd_id}.gcn3'
    gcnurl_template = 'https://gcn.nasa.gov/circulars?query={sd_id}'
    default_skymap_filename = 'bayestar.png'
    burst_skymap_filename = '{pipeline}.png'
    pe_results_tagname = 'pe_results'

    def get_queryset(self, **kwargs):
        # Query only for public events for the given observation run.
        # if it's not in the run list, return a 404.
        self.obsrun = self.kwargs.get('obsrun')
        if self.obsrun not in settings.PUBLIC_PAGE_RUNS:
            raise Http404

        qs = Superevent.objects.filter(is_exposed=True,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
            t_0__range=RUN_MAP[self.obsrun]) \
            .prefetch_related('voevent_set', 'log_set')
        return qs

    # Define insignificance per run:
    def significant_events(self, sevents):
        # We're checking for ADVREQ|ADVOK|ADVNO
        # https://git.ligo.org/computing/gracedb/server/-/issues/303#note_725082
        # So use Q filters for these:
        significant_filter = Q()
        if self.obsrun in ['ER15', 'O4']:
           significant_filter = Q(labels__name='ADVREQ') | \
                                Q(labels__name='ADVOK') | \
                                Q(labels__name='ADVNO')

        return sevents.filter(significant_filter)


    # and some documentation for the definition of significance.
    # Note: this value is also used as a trigger to show the significance
    # button and bullet.
    def insignificant_docs(self, run):
        if run in ['ER15', 'O4']:
            return 'https://emfollow.docs.ligo.org/userguide/content.html#significance'
        else:
            return None


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
        # skymap file in the VOEvent, so try the default. The name of a default
        # skymap will change if it's a burst event or not. 
        if skymap_image is None:
            # Burst events:
            if superevent.preferred_event.group.name == 'Burst':
                # Set up a filter for mixed (pipeline) case. 
                # In O4, the convention was all lower case, but O3 was mixed case. argghhhh
                skymap_log_list = public_logs.filter(filename__iexact=self.burst_skymap_filename.format(
                    pipeline=superevent.preferred_event.pipeline.name))

                if skymap_log_list.exists():
                    skymap_image = skymap_log_list.first().filename

            # Other events:
            elif public_logs.filter(filename=self.default_skymap_filename).exists():
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
        context = super(SupereventPublic, self).get_context_data(**kwargs)

        # For each superevent, get list of log messages and construct pastro
        # string
        table_data = {}
        candidates = 0
        retractions = 0

        # get insignificant events
        sig_events = self.significant_events(self.object_list)

        # Filter and loop over exposed superevents for the given run:
        for se in self.object_list:

            # External links to GCN notice and circular
            se.noticeurl = self.noticeurl_template.format(s_id=
                se.default_superevent_id)
            if self.obsrun == "O3":
                se.gcnurl = self.gcnurl_template_o3.format(sd_id=
                    se.default_superevent_id[1:])
            else:
                se.gcnurl = self.gcnurl_template.format(sd_id=
                    se.default_superevent_id)

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
            retractions += int(se.retract)

            # is the candidate significant?
            se.signif = se in sig_events

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
                    ("MassGap", voe.prob_mass_gap),]
                pastro_values.sort(reverse=True, key=lambda p_a: 0.0 if p_a[1] is None else p_a[1])
                sourcelist = []
                for key, value in pastro_values:
                    if value is None:
                        value = 0.0
                    if value > 0.01:
                        prob = int(round(100*value))
                        if prob == 100: prob = '>99'
                        sourcestr = "{0} ({1}%)".format(key, prob)
                        sourcelist.append(sourcestr)
                se.sourcetypes = ', '.join(sourcelist)


        # Now add it to the output dict, with the key being the run value:
        table_data['events'] =  self.object_list

        total_events = self.object_list.count()

        # export the dictionary for rendering:
        context['signif_docs'] = self.insignificant_docs(self.obsrun)
        context['data'] = table_data
        context['run'] = self.obsrun
        context['total_events'] = self.object_list.count()
        context['total_sig'] = sig_events.count()
        context['total_insig'] = context['total_events'] - context['total_sig']
        context['candidates'] = candidates
        context['retractions'] = retractions
        context['sig_cands'] = context['total_sig'] - retractions

        return context

# FIXME: this is vestigial code from a planned curated view. I'm going 
# to comment it out, but leave it.

#@method_decorator(public_if_public_access_allowed, name='dispatch')
#class SupereventCurated(DisplayFarMixin, ListView):
#    model = Superevent
#    template_name = 'superevents/curated_events.html'
#    filter_permissions = ['superevents.view_superevent']
#    log_view_permission = 'superevents.view_log'
#
#    # Curated event categories, differentiated by label:
#    catalog_label_names = ['O3A_CBC_CATALOG',
#                           'O3B_CBC_CATALOG',
#                           'O3A_CBC_SUBTHRESHOLD',
#                           'O3B_CBC_SUBTHRESHOLD',]
#
#    def get_queryset(self, **kwargs):
#        # Query only for public events
#        # NOTE: may want to fix this to only O3 events at some point
#        qs = Superevent.objects.filter(is_gw=True,
#            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION) \
#            .prefetch_related('voevent_set', 'log_set')
#        return qs
#
#    def get_context_data(self, **kwargs):
#        # Get base context
#        context = super(SupereventCurated, self).get_context_data(**kwargs)
#
#        candidates = self.object_list
#
#        for section_label in self.catalog_label_names:
#            context[section_label] = candidates.filter(labels__name=section_label)
#
#        context['curated_gws'] = candidates
#
#        return context
#
#
#class SupereventDetailCuratedView(OperatorSignoffMixin, AdvocateSignoffMixin,
#    ExposeHideMixin, ConfirmGwFormMixin, DisplayFarMixin,
#    PermissionsFilterMixin, DetailView):
#    """
#    Detail view for curated superevents.
#    """
#    model = Superevent
#    template_name = 'superevents/curated_detail.html'
#    filter_permissions = ['superevents.view_superevent']
#
#    def get_queryset(self):
#        """Get queryset and preload some related objects"""
#        qs = super(SupereventDetailCuratedView, self).get_queryset()
#
#        # Do some optimization
#        qs = qs.select_related('preferred_event__group',
#            'preferred_event__pipeline', 'preferred_event__search')
#        qs = qs.prefetch_related('labelling_set', 'events')
#
#        return qs
#
#    def get_object(self, queryset=None):
#        if queryset is None:
#            queryset = self.get_queryset()
#        superevent_id = self.kwargs.get('superevent_id')
#        obj = get_superevent_by_sid_or_gwid_or_404(superevent_id, queryset)
#        return obj
#
#    def get_context_data(self, **kwargs):
#        # Get base context
#        context = super(SupereventDetailCuratedView, self).get_context_data(**kwargs)
#
#        # Add a bunch of extra stuff
#        superevent = self.object
#        context['preferred_event'] = superevent.preferred_event
#        context['preferred_event_labelling'] = superevent.preferred_event \
#            .labelling_set.prefetch_related('label', 'creator').all()
#
#        # TODO: filter events for user? Not clear what information we want
#        # to show to different groups
#        # Pass event graceids
#        context['internal_events'] = superevent.get_internal_events() \
#            .order_by('id')
#        context['external_events'] = superevent.get_external_events() \
#            .order_by('id')
#
#        # Get display FARs for preferred_event
#        context.update(zip(
#            ['display_far', 'display_far_hr', 'far_is_upper_limit'],
#            self.get_display_far(obj=superevent.preferred_event)
#            )
#        )
#
#        # Is the user an external user? (I.e., not part of the LVC?) The
#        # template needs to know that in order to decide what pieces of
#        # information to show.
#        context['user_is_external'] = is_external(self.request.user)
#
#        # Get list of EMGroup names for emo creation form
#        context['emgroups'] = EMGroup.objects.all().order_by('name') \
#            .values_list('name', flat=True)
#
#        return context
