import logging
import os
from lal import gpstime
from django.views.generic.detail import DetailView
from django.views.generic import ListView

from guardian.shortcuts import get_objects_for_user

from core.file_utils import get_file_list
from events.models import EMGroup
from events.mixins import DisplayFarMixin
from events.permission_utils import is_external
from .mixins import ExposeHideMixin, OperatorSignoffMixin, \
    AdvocateSignoffMixin, PermissionsFilterMixin, ConfirmGwFormMixin
from .models import Superevent
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

class SupereventPublic(ListView):
    model = Superevent
    template_name = 'superevents/public.html'
    filter_permissions = ['superevents.view_superevent']
    log_view_permission = 'superevents.view_log'    

    def get_queryset(self, **kwargs):
        # -- Query only for public events
        qs = Superevent.objects.filter(is_exposed=True, category='P')  #-- Change cateogry to P for production
        return qs
        
    def get_context_data(self, **kwargs):
        # Get base context
        context = ListView.get_context_data(self, **kwargs)

        #-- For each superevent, get list of log messages and construct pastro string
        candidates = 0
        for se in context['object_list']:

            se.maplocal = "/apiweb/superevents/{0}/files/bayestar.png".format(se.superevent_id)

            #-- GCN links
            se.noticeurl = "https://gcn.gsfc.nasa.gov/notices_l/{0}.lvc".format(se.default_superevent_id)
            se.gcnurl    = "https://gcn.gsfc.nasa.gov/other/GW{0}.gcn3".format(se.default_superevent_id[1:])
            
            se.ifar_yrs = 1.0 / (se.far*3600*24*365.0)
            se.t0_iso = gpstime.gps_to_utc(se.t_0).isoformat(' ').split('.')[0]
            se.t0_utc = se.t0_iso.split()[1]
            
            #-- Get list of voevents
            voevents = se.voevent_set.all()

            # -- Filter out retractions
            good_voevents = sorted([voe for voe in voevents if voe.voevent_type != 'RE'],key=lambda voe:voe.N)
            
            # -- Find retractions
            retraction_list = [voe for voe in voevents if voe.voevent_type == 'RE']
            if len(retraction_list) > 0:
                se.retract = True
            else:
                se.retract = False
                candidates += 1


            viewable_logs = get_objects_for_user(self.request.user,
                                                 self.log_view_permission,
                                                 se.log_set.all()).filter(tags__name='analyst_comments') #-- change to analyst_comments
            

            se.comments = ' ** '.join([log.comment for log in viewable_logs]) 
            if se.retract: se.comments += " ** RETRACTED ** "
            
            # -- Read out probabilities
            voe = good_voevents[-1]
            pastro_values = [ ("BNS",voe.prob_bns), ("NSBH",voe.prob_nsbh),
                              ("BBH", voe.prob_bbh), ("Terrestrial", voe.prob_terrestrial),
                              ("MassGap", voe.prob_mass_gap) ]

            pastro_values.sort(reverse=True, key=lambda (a,b):b)
            sourcelist = []
            for key, value in pastro_values:
                if value > 0.01:
                    prob = int(round(100*value))
                    if prob == 100: prob = '>99'
                    sourcestr = "{0} ({1}%)".format(key, prob)
                    sourcelist.append(sourcestr)
            se.sourcetypes = ', '.join(sourcelist)
            se.N = voe.N

            
        context['candidates']=candidates

        #-- Is this user outside the LVC?
        context['user_is_external'] = is_external(self.request.user)
        
        return context


    
