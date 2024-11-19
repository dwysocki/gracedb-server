from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from events.models import Event, EventLog, GrbEvent, NeutrinoEvent, \
    CoincInspiralEvent, MLyBurstEvent, MultiBurstEvent, LalInferenceBurstEvent, \
    SingleInspiral, SimInspiralEvent
from api.utils import api_reverse
from superevents.models import Superevent

# Fields in the siminspiral table to expose to public:

snglinsp_public_fields = ['ifo','end_time','end_time_ns']
multiburst_public_fields = ['ifos', 'single_ifo_times']

# define a function that returns a tuple of the superevent window range:
def superevent_window_range(gpstime):
    return (gpstime - settings.EVENT_SUPEREVENT_WINDOW_BEFORE, \
            gpstime + settings.EVENT_SUPEREVENT_WINDOW_AFTER)

class GRBEventSerializer(serializers.ModelSerializer):
    T90 = serializers.SerializerMethodField()

    class Meta:
        model = GrbEvent
        fields =('author_ivorn', 'dec', 'designation', 'redshift', \
                 'how_description', 'coord_system', 'trigger_id', 'error_radius', \
                 'how_reference_url', 'ra', 'ivorn', 'trigger_duration', \
                 'author_shortname', 'T90', 'observatory_location_id')

    def get_T90(self, obj):
        return obj.t90

class NeutrinoEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NeutrinoEvent
        fields =('ivorn', 'coord_system', 'ra', 'dec', 'error_radius', \
                 'far_ne', 'far_unit', 'signalness', 'energy', 'src_error_90', \
                 'src_error_50', 'amon_id', 'run_id', 'event_id', 'stream')

class CoincInspiralEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoincInspiralEvent
        fields = ('ifos', 'end_time', 'end_time_ns', 'mass', 'mchirp',
                  'minimum_duration', 'snr', 'false_alarm_rate', 'combined_far')

class MLyBurstEventSerializer(serializers.ModelSerializer):
    scores = serializers.SerializerMethodField()
    SNR = serializers.SerializerMethodField()

    class Meta:
        model = MLyBurstEvent
        fields =('ifos', 'central_freq', 'bandwidth', 'duration', 'central_time', \
                 'detection_statistic', 'SNR', 'bbh', 'sglf', 'sghf', \
                 'background', 'glitch', 'freq_correlation', 'channels', 'scores')

    def to_representation(self, obj):
        channels_out = None
        ret = super().to_representation(obj)
        if obj.channels:
            channels_out = obj.channels.split(',')
        ret['channels'] = channels_out
        return ret

    def get_scores(self, obj):
        return {'coherency': obj.score_coher,
                'coincidence': obj.score_coinc,
                'combined': obj.score_comb}

    def get_SNR(self, obj):
        return obj.snr


class MultiBurstEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultiBurstEvent
        fields =('ifos', 'start_time', 'start_time_ns', 'duration', 'strain', \
                 'peak_time', 'peak_time_ns', 'central_freq', 'bandwidth', \
                 'amplitude', 'mchirp', 'snr', 'confidence', 'false_alarm_rate', \
                 'ligo_axis_ra', 'ligo_axis_dec', 'ligo_angle', 'ligo_angle_sig', \
                 'single_ifo_times', 'hoft', 'code')

    def __init__(self, *args, is_external=False, **kwargs):
        super().__init__(*args, **kwargs)

        if is_external:
            self.fields =  {field_name: self.fields[field_name] \
                for field_name in multiburst_public_fields}


class LalInferenceBurstEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LalInferenceBurstEvent
        fields =('bci', 'quality_mean', 'quality_median', 'bsn', \
                 'omicron_snr_network', 'omicron_snr_H1', 'omicron_snr_L1', \
                 'omicron_snr_V1', 'hrss_mean', 'hrss_median', 'frequency_mean', \
                 'frequency_median')

class SimInspiralEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimInspiralEvent
        fields =('mass1', 'mass2', 'eta', 'coa_phase', 'mchirp', 'spin1x', \
                 'spin1y', 'spin1z', 'spin2x', 'spin2y', 'spin2z', 'end_time_gmst', \
                 'f_lower', 'f_final', 'distance', 'latitude', 'longitude', \
                 'polarization', 'inclination', 'theta0', 'phi0', 'alpha', 'beta', \
                 'psi0', 'psi3', 'alpha1', 'alpha2', 'alpha3', 'alpha4', 'alpha5', \
                 'alpha6', 'eff_dist_g', 'eff_dist_h', 'eff_dist_l', 'eff_dist_t', \
                 'eff_dist_v', 'amplitude', 'tau', 'phi', 'freq', 'amp_order', \
                 'geocent_end_time', 'geocent_end_time_ns', 'numrel_mode_min', \
                 'numrel_mode_max', 'bandpass', 'g_end_time', 'g_end_time_ns', \
                 'h_end_time', 'h_end_time_ns', 'l_end_time',  'l_end_time_ns', \
                 't_end_time', 't_end_time_ns', 'v_end_time', 'v_end_time_ns', \
                 'waveform', 'numrel_data', 'source',  'taper', 'source_channel', \
                 'destination_channel')

class SingleInspiralSerializer(serializers.ModelSerializer):
    class Meta:
        model = SingleInspiral
        fields = ('ifo', 'search', 'channel', 'end_time', 'end_time_ns', \
                  'end_time_gmst', 'impulse_time', 'impulse_time_ns', \
                  'template_duration', 'event_duration', 'amplitude', \
                  'eff_distance', 'coa_phase', 'mass1', 'mass2', 'mchirp', \
                  'mtotal', 'eta', 'kappa', 'chi', 'tau0', 'tau2', 'tau3', \
                  'tau4', 'tau5', 'ttotal', 'psi0', 'psi3', 'alpha', \
                  'alpha1', 'alpha2', 'alpha3', 'alpha4', 'alpha5', 'alpha6', \
                  'beta', 'f_final', 'snr', 'chisq', 'chisq_dof', 'bank_chisq', \
                  'bank_chisq_dof', 'cont_chisq', 'cont_chisq_dof', 'sigmasq', \
                  'rsqveto_duration', 'Gamma0', 'Gamma1', 'Gamma2', 'Gamma3', \
                  'Gamma4', 'Gamma5', 'Gamma6', 'Gamma7', 'Gamma8', 'Gamma9', \
                  'spin1x', 'spin1y', 'spin1z', 'spin2x', 'spin2y', 'spin2z')

    def __init__(self, *args, is_external=False, **kwargs):
        super().__init__(*args, **kwargs)

        if is_external:
            self.fields =  {field_name: self.fields[field_name] \
                for field_name in snglinsp_public_fields}

# This dict maps the key in the extra_attributes dict to its corresponding
# event subclass name. SingleInspiral events are a little different, so do
# that separately for now.

EVENT_ATTRIBUTE_MAP = {
    GrbEvent: ('GRB', 'grbevent', GRBEventSerializer),
    NeutrinoEvent: ('NeutrinoEvent', 'neutrinoevent', NeutrinoEventSerializer),
    CoincInspiralEvent: ('CoincInspiral', 'coincinspiralevent', CoincInspiralEventSerializer),
    MLyBurstEvent: ('MLyBurst', 'mlyburstevent', MLyBurstEventSerializer),
    MultiBurstEvent: ('MultiBurst', 'multiburstevent', MultiBurstEventSerializer),
    LalInferenceBurstEvent: ('LalInferenceBurst', 'lalinferenceburstevent', LalInferenceBurstEventSerializer),
    SimInspiralEvent: ('SimInspiral', 'siminspiralevent', SimInspiralEventSerializer),
}

class EventSerializer(serializers.ModelSerializer):
    # Fields.
    group = serializers.CharField(source="group.name")
    pipeline = serializers.CharField(source="pipeline.name")
    search = serializers.CharField(source="search.name", allow_null=True)
    submitter = serializers.SlugRelatedField(slug_field="username",
                    read_only=True)

    # New fields.
    labels = serializers.SerializerMethodField('get_labels')
    far_is_upper_limit = serializers.SerializerMethodField()
    extra_attributes = serializers.SerializerMethodField(allow_null=True)
    links = serializers.SerializerMethodField('get_links')
    superevent_neighbours = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(EventSerializer, self).__init__(*args, **kwargs)
        self.request = self.context.get('request', None)
        self.external = self.context.get('request_is_external', False)

        # don't include neighboring superevents if this is nested inside itself
        self.is_nested = self.context.get('is_nested', False)

        # don't include neighboring superevents for serializations that aren't
        # alerts. 
        self.is_alert = self.context.get('is_alert', False)
        if not self.is_alert or self.is_nested:
            self.fields.pop('superevent_neighbours')


    class Meta:
        model = Event
        fields = ('submitter', 'created', 'group',
                  'pipeline', 'graceid', 'gpstime', 'reporting_latency',
                  'instruments', 'nevents', 'offline',
                  'search', 'far', 'far_is_upper_limit', 'likelihood',
                  'labels', 'extra_attributes', 'superevent', 'links',
                  'superevent_neighbours')

    def to_representation(self, obj):
        display_far, far_is_upper_limit = self.display_far_and_limit(obj)
        ret = super().to_representation(obj)
        ret['far'] = display_far
        ret['superevent'] = obj.superevent.superevent_id if obj.superevent else None
        ret['far_is_upper_limit'] = far_is_upper_limit
        return ret

    # modify the display far and limit parameter. TODO this same code is
    # duplicated in at least (?) two other places, it should really get
    # combined into one function. really though, it's probably not even
    # necessary since the VOEVENT_FAR_FLOOR is zero (and so not used...)
    # but who knows, it might come back at some point.
    def display_far_and_limit(self, obj):
        far_is_upper_limit = False
        display_far = obj.far
        if obj.far and self.external and obj.far < settings.VOEVENT_FAR_FLOOR:
            display_far = settings.VOEVENT_FAR_FLOOR
            far_is_upper_limit = True

        return display_far, far_is_upper_limit
        

    def get_labels(self, obj):
        return [label.name for label in obj.labels.all()]

    def display_far_floor(self, obj):
        if obj.far and self.external and obj.far < settings.VOEVENT_FAR_FLOOR:
            return True
        else:
            return False

    def get_links(self, obj):
        graceid = obj.graceid
        return {
            "neighbors" : api_reverse("events:neighbors", args=[graceid], request=self.request),
            "log"   : api_reverse("events:eventlog-list", args=[graceid], request=self.request),
            "files" : api_reverse("events:files", args=[graceid], request=self.request),
            "labels" : api_reverse("events:labels", args=[graceid], request=self.request),
            "self"  : api_reverse("events:event-detail", args=[graceid], request=self.request),
            "tags"  : api_reverse("events:eventtag-list", args=[graceid], request=self.request),
            }

    # This is a dummy placeholder since it gets overwritten by to_representation
    def get_far_is_upper_limit(self, obj):
        return False


    def get_extra_attributes(self, obj):
        extra_attrs_dict = {}

        # Include this section for requests by internal users and
        # FIXME alert contents:
        if (self.request is not None and not self.external) or self.is_alert or self.is_nested:
            for subevent_type, subevent_vals in EVENT_ATTRIBUTE_MAP.items():
                if isinstance(obj, subevent_type):
                    extra_attrs_dict.update({subevent_vals[0]:
                        subevent_vals[2](getattr(obj, subevent_vals[1])).data})

            # For CoincInspiral events, append the SingleInspiral data, after
            # checking to see if the tables are actually there, just to be sure.
            if isinstance(obj, CoincInspiralEvent):
                if obj.singleinspiral_set.exists():
                    extra_attrs_dict.update({'SingleInspiral':
                    [SingleInspiralSerializer(e, is_external=self.external).data for e in obj.singleinspiral_set.all()]
                    })

        # For the special inexplicable case where the user is external, then
        # return specific fields from SingleInspiral or multiburst events
        elif (self.request is not None and self.external):
            if isinstance(obj, CoincInspiralEvent):
                extra_attrs_dict.update({'SingleInspiral':
                [SingleInspiralSerializer(e, is_external=self.external).data \
                    for e in obj.singleinspiral_set.all()]})
            elif isinstance(obj, MultiBurstEvent):
                extra_attrs_dict.update({'MultiBurst':
                    MultiBurstEventSerializer(obj, is_external=self.external).data})

        
        return extra_attrs_dict


    def get_superevent_neighbours(self, obj):
        return_dict = {}

        # Look for neighbors only if the event has a valid gpstime. This will
        # probably trigger if event.gpstime=0.0, but that event isn't valid anyway.
        if obj.gpstime:
            for s in self.superevent_neighbours_set(obj):
                sn_dict = {}

                # Add superevent_id:
                sn_dict.update({
                    'superevent_id': s.superevent_id,
                    })

                # Add gw_events:
                sn_dict.update({
                    'gw_events': [g.graceid for g in s.get_internal_events()],
                    })

                # Add basic superevent info:
                sn_dict.update({
                    'far': s.far,
                    't_start': s.t_start,
                    't_0': s.t_0,
                    't_end': s.t_end,
                    })

                # Add labels:
                sn_dict.update({
                    'labels': [l.name for l in s.labels.all()],
                    })

                # Add preferred_event:
                sn_dict.update({
                    'preferred_event': s.preferred_event.graceid,
                    })

                # Add preferred_event_data:
                sn_dict.update({
                    'preferred_event_data':
                     EventSerializer(s.preferred_event.get_subclass(),
                         context={'is_nested': True}).data,
                    })

                # Add this info to the response
                return_dict.update(
                    {s.superevent_id: sn_dict})

        return return_dict

    def superevent_category(self, obj):
        # return the corresponding superevent category of the event
        if obj.is_production():
            return Superevent.SUPEREVENT_CATEGORY_PRODUCTION
        elif obj.is_mdc():
            return Superevent.SUPEREVENT_CATEGORY_MDC
        elif obj.is_test():
            return Superevent.SUPEREVENT_CATEGORY_TEST


    def superevent_neighbours_set(self, obj):
        # query the database for nearby superevents
        return Superevent.objects.filter(
            t_0__range=superevent_window_range(obj.gpstime),
            category=self.superevent_category(obj)) \
            .prefetch_related('events', 'labels') \
            .select_related('preferred_event', 'preferred_event__pipeline',
                'preferred_event__group',
                'preferred_event__search',
                'preferred_event__submitter',
                'preferred_event__superevent',
                'preferred_event__grbevent',
                'preferred_event__neutrinoevent',
                'preferred_event__coincinspiralevent',
                'preferred_event__mlyburstevent',
                'preferred_event__multiburstevent',
                'preferred_event__lalinferenceburstevent',
                'preferred_event__siminspiralevent',
             )



class EventLogSerializer(serializers.ModelSerializer):
    """docstring for EventLogSerializer"""
    comment =  serializers.CharField(required=True, max_length=200)
    class Meta:
        model = EventLog
        fields = ('comment', 'issuer', 'created')
