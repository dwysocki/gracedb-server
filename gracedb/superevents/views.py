import logging
import os
from lal import gpstime

from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.views.generic.detail import DetailView
from django.views.generic import ListView

from guardian.shortcuts import get_objects_for_user

from core.file_utils import get_file_list, flexible_skymap_to_png
from core.time_utils import utc_datetime_decimal_seconds
from core.utils import display_far_hz_to_yr
from events.models import EMGroup
from events.models import Label
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from events.templatetags.mediaviews import tag_selecter
from ligoauth.decorators import public_if_public_access_allowed
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin, PermissionsFilterMixin, ConfirmGwFormMixin, \
    RRTViewMixin, AreAccessManagersMixin
from .models import Superevent, VOEvent, Log
from search.constants import RUN_MAP
from search.utils import run_map_search_filter
from .utils import get_superevent_by_date_id_or_404, \
    get_superevent_by_sid_or_gwid_or_404


# Set up logger
logger = logging.getLogger(__name__)


class SupereventDetailView(OperatorSignoffMixin, AdvocateSignoffMixin,
    RRTViewMixin, ExposeHideMixin, ConfirmGwFormMixin, DisplayFarMixin,
    AreAccessManagersMixin, PermissionsFilterMixin, DetailView):
    """
    Detail view for superevents.
    """
    model = Superevent
    template_name = 'superevents/detail.html'
    filter_permissions = ['superevents.view_superevent']
    time_fmt = '%Y-%m-%d %H:%M:%S.%f'

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

    def get_gw_event_details(self, superevent=None):

        # Start with the list of gw_events:
        gw_events = superevent.get_internal_events() \
                        .select_related('group', 'pipeline', 'search') \
                        .prefetch_related('labelling_set', 'eventlog_set') \
                        .order_by('id')

        # Loop over events and get info: 
        for gw in gw_events:

            # Get when the event was added to the superevent:
            added = gw.eventlog_set.filter(comment__contains='Added to superevent')
            # Get when (and if) the event was set as preferred:
            set_as_preferred = gw.eventlog_set.filter(comment__contains='Set as preferred')
            if added.exists():
                gw.added_to_superevent = utc_datetime_decimal_seconds(added.last().created)
            elif set_as_preferred.exists():
                gw.added_to_superevent = utc_datetime_decimal_seconds(set_as_preferred.first().created)

            if set_as_preferred.exists():
                gw.set_as_preferred = utc_datetime_decimal_seconds(set_as_preferred.first().created)

            # when the superevent was uploaded:
            gw.created_pretty = utc_datetime_decimal_seconds(gw.created)

        return gw_events


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
        context['internal_events'] = self.get_gw_event_details(superevent)
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
        context['log_list'] = superevent.log_set.filter(**log_set_query_kwargs) \
                              .select_related('issuer') \
                              .prefetch_related('tags')

        # Render the tag selecter html
        template = tag_selecter()
        context['tag_selecter_name'] = mark_safe(template.format(form_name='name'))
        context['tag_selecter_tagname'] = mark_safe(template.format(form_name='tagname'))

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
#@method_decorator(cache_page(0), name='dispatch')
@method_decorator(cache_page(settings.PUBLIC_PAGE_CACHING), name='dispatch')
@method_decorator(vary_on_headers('X-Requested-With'), name='dispatch')
@method_decorator(public_if_public_access_allowed, name='dispatch')
class SupereventPublic(DisplayFarMixin, ListView):
    model = Superevent
    paginate_by = settings.PUBLIC_PAGE_RESULTS
    template_name = 'superevents/public_alerts.html'
    filter_permissions = ['superevents.view_superevent']
    log_view_permission = 'superevents.view_log'
    noticeurl_template = 'https://gcn.gsfc.nasa.gov/notices_l/{s_id}.lvc'
    gcnurl_template_o3 = 'https://gcn.gsfc.nasa.gov/other/GW{sd_id}.gcn3'
    gcnurl_template = 'https://gcn.nasa.gov/circulars?query={sd_id}'
    default_skymap_filename = 'bayestar.png'
    burst_skymap_filename = '{pipeline}.png'
    show_button_text = 'Show All Public Events'
    hide_button_text = 'Show Significant Events Only'
    button_text_dict = {'show_button_text': show_button_text,
            'hide_button_text': hide_button_text
            }
    skymap_cache_key = '{sid}-skymap'

    # Override the standard get() method to allow for browser vs ajax requests.
    def get(self, request, **args):
        # For ajax requests, optionally get the "showall" value to to reveal
        # insignificant events. Otherwise, for browser requests (the default when
        # a user first lands on the public page), then only show significant.
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if self.get_paginate_by(self.object_list) is not None and hasattr(
                self.object_list, "exists"
            ):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404(
                    _("Empty list and “%(class_name)s.allow_empty” is False.")
                    % {
                        "class_name": self.__class__.__name__,
                    }
                )

        showall = request.GET.get('showall', None)
        if showall and showall.lower() in ['true', 't', '1', 'y']:
            showall=True
            button_text = self.hide_button_text
        else:
            showall=False
            button_text = self.show_button_text

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object_list = self.get_queryset(showall)
            context = self.get_context_data()
            context['showall'] = int(showall)
            context['button_text'] = button_text
            rendered_table = render_to_string('superevents/public_alerts_table.html',
                    context=context, request=request)
            data = {'rendered_table': rendered_table}
            return JsonResponse(data)
        else:
            self.object_list = self.get_queryset(showall)
            context = self.get_context_data()
            context['showall'] = int(showall)
            context['button_text'] = button_text
            return render(request, self.template_name, context=context)


    # Modify get_queryset() to filter for significant vs insignificant:
    def get_queryset(self, showall=False, **kwargs):
        if showall:
            superevents = self.get_public_superevents()
        else:
            superevents = self.significant_events(self.get_public_superevents())

        return (
            superevents
            .prefetch_related(Prefetch('log_set',
                queryset=Log.objects.filter(filename__contains='omegascan'),
                to_attr='omega_scan_logs'))
            .select_related('preferred_event', 'preferred_event__group', 'preferred_event__pipeline')
        )


    # Get all publicly exposed production superevents:
    def get_public_superevents(self, **kwargs):
        # Query only for public events for the given observation run.
        # if it's not in the run list, return a 404.
        self.obsrun = self.kwargs.get('obsrun')
        if self.obsrun not in settings.PUBLIC_PAGE_RUNS:
            raise Http404

        # The base query for exposed production superevents:
        qs = Superevent.objects.filter(is_exposed=True,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)
         
        # return the events in the date range:
        return qs.filter(run_map_search_filter(self.obsrun, 't_0'))


    # Define significance per run:
    def significant_events(self, sevents):
        # We're checking for ADVREQ|ADVOK|ADVNO
        # https://git.ligo.org/computing/gracedb/server/-/issues/303#note_725082
        # So use Q filters for these:
        significant_filter = Q()
        if self.obsrun in ['ER15', 'ER16', 'O4a', 'O4b', 'O4c', 'O4']:
           significant_filter = Q(labels__name='ADVREQ') | \
                                Q(labels__name='ADVOK') | \
                                Q(labels__name='ADVNO')

        return sevents.filter(significant_filter)

    # Get events with ADVNO:
    def retracted_events(self, sevents):
        retraction_filter = Q(labels__name='ADVNO')

        return sevents.filter(retraction_filter)


    # and some documentation for the definition of significance.
    # Note: this value is also used as a trigger to show the significance
    # button and bullet.
    def insignificant_docs(self, run):
        if run in ['ER15', 'ER16', 'O4a', 'O4b', 'O4c', 'O4']:
            return 'https://emfollow.docs.ligo.org/userguide/content.html#significance'
        else:
            return None


    def get_skymap_image(self, superevent, voevent=None):
        skymap_image = None
        skymap_log_object = None
        public_logs = superevent.log_set.filter(tags__name='public')

        # Try to get skymap from latest non-retraction VOEvent
        if voevent is not None and voevent.skymap_filename is not None:
            # Assume filename is the same, with a different suffix.
            voevent_skymap_image, version = flexible_skymap_to_png(voevent.skymap_filename) 

            # See if a public log exists with that filename:
            if version:
                skymap_log = public_logs.filter(filename=voevent_skymap_image,
                       file_version=version).order_by('-file_version')
            else: 
                skymap_log = public_logs.filter(filename=voevent_skymap_image)\
                       .order_by('-file_version')

            skymap_log_object = skymap_log.first()

        # If skymap_log_object is None, we didn't find a file based on the
        # skymap file in the VOEvent, so try the default. The name of a default
        # skymap will change if it's a burst event or not. 
        if skymap_log_object is None:
            # Burst events:
            if superevent.preferred_event.group.name == 'Burst':
                # Set up a filter for mixed (pipeline) case. 
                # In O4, the convention was all lower case, but O3 was mixed case. argghhhh
                skymap_log = public_logs.filter(
                        filename__iexact=self.burst_skymap_filename.format(
                            pipeline=superevent.preferred_event.pipeline.name))

                skymap_log_object = skymap_log.first()
            # aframe events:
            elif superevent.preferred_event.pipeline.name == 'aframe':
                skymap_image = reverse(
                    'legacy_apiweb:default:superevents:superevent-file-detail',
                    args=[superevent.default_superevent_id, 'amplfi.png']
                )
            # Other events:
            else:
                skymap_log = public_logs.filter(filename=self.default_skymap_filename)
                skymap_log_object = skymap_log.first()

        if skymap_log_object:
            # Add version to image name to be safe
            skymap_image = skymap_log_object.versioned_filename

            skymap_image = reverse(
                'legacy_apiweb:default:superevents:superevent-file-detail',
                args=[superevent.default_superevent_id, skymap_image]
            )
        return skymap_image


    def get_context_data(self, **kwargs):
        context = super(SupereventPublic, self).get_context_data(**kwargs)

        # Get the total number of public events:
        context['total_events'] = self.get_public_superevents().count()

        # Determine if this is an external request:
        external_user = is_external(self.request.user)

        # get insignificant events
        sig_events = list(self.significant_events(self.get_public_superevents()))

        # get retracted events, and count the number of candidates and
        # and retractions:
        retracted_events = list(self.retracted_events(self.get_public_superevents()))
        retractions = len(retracted_events)
        candidates = self.object_list.count() - retractions

        # prefetch the latest, non-retraction voevent. it's used in two places
        # in the loop below:
        #    1) to get the skymap name
        #    2) to get p_astro quantities

        voe_query = VOEvent.objects.filter(superevent__in=self.object_list)\
                                    .exclude(voevent_type=VOEvent.VOEVENT_TYPE_RETRACTION)\
                                    .order_by('superevent_id', '-N')\
                                    .distinct('superevent_id').select_related('superevent')

        # construct a dictionary where the key is a superevent_id and the value is the
        # associated voevent from the query above. This hits the database for every one of
        # the voevents, but it's outside the loop so it should only have to do this once:

        voevent_dict = {vo.superevent.superevent_id: vo for vo in voe_query}

        # Construct a queryset for all the public, analyst_comment log messages that are
        # part of the object_list. This is going to be a small, small subset compared to 
        # the total number of superevents:

        public_comments_set = Log.objects.filter(superevent__in=self.object_list)\
                                         .filter(tags__name='public')\
                                         .filter(tags__name='analyst_comments')\
                                         .select_related('superevent')\
                                         .prefetch_related('tags')

        # Construct a list of unique superevent ids that have public analyst comments.
        # This hits the database once:
        public_comments_sids = list(public_comments_set.values_list('superevent__superevent_id', flat=True).distinct())

        # Construct a dictionary where the key is a superevent_id and the value is the
        # associated concatenated comment. This hits the database once for each value
        # in public_comments_sids. But again this is less than O(1%) or less than the
        # total number of public superevents:

        comments_dict = {}

        for sid in public_comments_sids:
             comments_dict.update(
                 {sid: ' ** '.join(public_comments_set.filter(superevent__superevent_id=sid)\
                                             .values_list('comment', flat=True))})

        ## Filter and loop over exposed superevents for the given run:
        ## This is the main object loop:
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

            if external_user and (se.far < settings.VOEVENT_FAR_FLOOR):
                se.far_hz = settings.VOEVENT_FAR_FLOOR
            else:
                se.far_hz = se.far

            se.far_hr = display_far_hz_to_yr(se.far_hz)

            # Get the latest, non-retraction voevent:
            voe = voevent_dict.get(se.superevent_id, None)

            # Get skymap image (if a public one exists). First see if the value is
            # cached for the current superevent (key is superevent_id
            se.skymap_image = cache.get(
                self.skymap_cache_key.format(sid=se.superevent_id))
            if not se.skymap_image:
                se.skymap_image = self.get_skymap_image(se, voe)
                cache.set(self.skymap_cache_key.format(sid=se.superevent_id),
                    se.skymap_image, settings.PUBLIC_PAGE_CACHING)

            # Was the candidate retracted?
            se.retract = se in retracted_events
            # is the candidate significant?
            se.signif = se in sig_events

            # get the analyst comments from the comments_dict using the current
            # superevent_id, otherwise return a blank string.
            se.comments = comments_dict.get(se.superevent_id, '')
            if se.retract:
                if se.comments:
                    se.comments = " ** " + se.comments
                se.comments = "RETRACTED" + se.comments

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


        # export the dictionary for rendering:
        context['signif_docs'] = self.insignificant_docs(self.obsrun)
        context['events'] = self.object_list
        context['run'] = self.obsrun
        context['total_sig'] = len(sig_events)
        context['total_insig'] = context['total_events'] - context['total_sig']
        context['candidates'] = candidates
        context['retractions'] = retractions
        context['sig_cands'] = context['total_sig'] - retractions

        # export the button text:
        context.update(self.button_text_dict)

        # update pagination context:
        page_size = self.get_paginate_by(self.object_list)
        context_object_name = self.get_context_object_name(self.object_list)
        if page_size:
            paginator, page, self.object_list, is_paginated = self.paginate_queryset(
                self.object_list, page_size
            )
            context.update({
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "object_list": self.object_list,
            })
        else:
            context.update({
                "paginator": None,
                "page_obj": None,
                "is_paginated": False,
                "object_list": queryset,
            })

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
