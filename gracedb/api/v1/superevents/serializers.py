from __future__ import absolute_import
import functools
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework import fields, serializers, validators
from rest_framework.exceptions import ValidationError

from events.models import Event, Label, Tag, EMGroup
from superevents.models import Superevent, Labelling, Log, VOEvent, \
    EMObservation, EMFootprint, Signoff, SupereventGroupObjectPermission
from .settings import SUPEREVENT_LOOKUP_URL_KWARG
from ..fields import ParentObjectDefault, DelimitedOrListField, \
    ChoiceDisplayField, CustomDecimalField
from ..events.fields import EventGraceidField
from ...utils import api_reverse

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


class SupereventSerializer(serializers.ModelSerializer):
    # Error messages
    default_error_messages = {
        'event_assigned': _('Event {graceid} is already assigned to a '
                            'Superevent'),
        'category_mismatch': _('Event {graceid} is of type \'{e_category}\', '
                               'and cannot be assigned to a superevent of '
                               'type \'{s_category}\''),
        'protected_label': _('The following label(s) are managed by an'
                             'automated process and cannot be manually added: '
                             '{labels}'),
    }
    # Use CustomDecimalField for underlying model DecimalFields
    serializer_field_mapping = \
        serializers.ModelSerializer.serializer_field_mapping
    serializer_field_mapping[models.DecimalField] = CustomDecimalField

    # Fields
    submitter = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    preferred_event = EventGraceidField(required=True,
        style={'base_template': 'input.html'})
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    category = ChoiceDisplayField(required=True,
        choices=Superevent.SUPEREVENT_CATEGORY_CHOICES)

    # Add custom fields
    superevent_id = serializers.SerializerMethodField(read_only=True)
    gw_events = serializers.SerializerMethodField(read_only=True)
    em_events = serializers.SerializerMethodField(read_only=True)
    links = serializers.SerializerMethodField(read_only=True)
    labels = serializers.SlugRelatedField(slug_field='name', many=True,
        queryset=Label.objects.all(), required=False)
    # Write only fields (user field is used to set submitter for instance
    # creation)
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    events = DelimitedOrListField(required=False, write_only=True,
        child=EventGraceidField())

    class Meta:
        model = Superevent
        fields = ('superevent_id', 'gw_id', 'category', 'created', 'submitter',
            'preferred_event', 'events', 't_start', 't_0', 't_end',
            'gw_events', 'em_events', 'far', 'labels', 'links', 'user')

    def validate(self, data):
        data = super(SupereventSerializer, self).validate(data)
        preferred_event = data.get('preferred_event')
        events = data.get('events')
        category = data.get('category')
        labels = data.get('labels')
        category_display = \
            dict(Superevent.SUPEREVENT_CATEGORY_CHOICES)[category]

        # Make sure preferred_event is not already assigned
        if (preferred_event.superevent or hasattr(preferred_event,
            'superevent_preferred_for')):
            self.fail('event_assigned', graceid=preferred_event.graceid)

        # Check that preferred_event has the correct type for the superevent
        # it's being assigned to
        if not Superevent.event_category_check(preferred_event, category):
            self.fail('category_mismatch', graceid=preferred_event.graceid,
                e_category=preferred_event.get_event_category(),
                s_category=category_display)

        # Make sure the events are not already assigned to a superevent
        if events:
            for ev in events:
                if (ev.superevent or hasattr(ev, 'superevent_preferred_for')):
                    self.fail('event_assigned', graceid=ev.graceid)
                # Check each event for type compatibility
                if not Superevent.event_category_check(ev, category):
                    self.fail('category_mismatch', graceid=ev.graceid,
                        e_category=ev.get_event_category(),
                        s_category=category_display)

        # Can't add protected labels to a superevent
        if labels:
            protected_labels = [l.name for l in labels if l.protected]
            if protected_labels:
                self.fail('protected_label',
                    labels=', '.join(protected_labels))

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import create_superevent
        submitter = validated_data.pop('user')

        return create_superevent(submitter, **validated_data)

    # Custom method fields ----------------------------------------------------
    def get_superevent_id(self, obj):
        """Override superevent_id (flexible) with default_superevent_id"""
        return obj.default_superevent_id

    def get_gw_events(self, obj):
        return [ev.graceid for ev in obj.get_internal_events()]

    def get_em_events(self, obj):
        return [ev.graceid for ev in obj.get_external_events()]

    def get_links(self, obj):
        bound_reverse = functools.partial(api_reverse,
            args=[obj.superevent_id],
            request=self.context.get('request', None))
        link_dict = {
            'events': bound_reverse('superevents:superevent-event-list'),
            'labels': bound_reverse('superevents:superevent-label-list'),
            'logs': bound_reverse('superevents:superevent-log-list'),
            'files': bound_reverse('superevents:superevent-file-list'),
            'self': bound_reverse('superevents:superevent-detail'),
            'voevents': bound_reverse('superevents:superevent-voevent-list'),
            'emobservations': bound_reverse(
                'superevents:superevent-emobservation-list'),
        }
        request = self.context.get('request', None)
        # Remove events link for anonymous users
        if request and request.user.is_anonymous:
            link_dict.pop('events')
        return link_dict

    def to_representation(self, instance):
        # Get default serializer response
        ret = super(SupereventSerializer, self).to_representation(instance)

        # Customize display for unauthenticated users
        request = self.context.get('request', None)
        if request and request.user.is_anonymous:
            ret.pop('gw_events')
            ret.pop('em_events')
            ret.pop('preferred_event')
        return ret


class SupereventUpdateSerializer(SupereventSerializer):
    """
    Used for updates ONLY (PUT/PATCH). Overrides validation which is needed
    for object creation.
    """
    allowed_fields = ('t_start', 't_0', 't_end', 'preferred_event')

    def __init__(self, *args, **kwargs):
        super(SupereventUpdateSerializer, self).__init__(*args, **kwargs)
        # Set all fields except self.allowed_fields to be read_only.
        # Safeguard against attempts to set other attributes through this
        # resource, but still allows us to return the same serialized object
        # as for the serializer that this inherits from
        for name in self.fields:
            if name not in self.allowed_fields:
                self.fields.get(name).read_only = True

    def validate(self, data):
        # We don't want to use the SupereventSerializer's validate method,
        # which is why we use that class in the super() call here
        data = super(SupereventSerializer, self).validate(data)
        preferred_event = data.get('preferred_event')

        # Only pass through attributes which are being changed
        updated_attributes = {k: v for k,v in data.items()
            if getattr(self.instance, k, None) != v}

        # Fail if nothing would be updated
        if not updated_attributes:
            raise ValidationError('Request would not modify the superevent')

        # Make sure preferred_event is not already assigned
        if preferred_event and (self.instance.preferred_event != 
            preferred_event):

            # But it's OK if this event is already attached to this superevent
            # We only fail if the event that we are trying to set as preferred
            # is attached to a different superevent
            if ((preferred_event.superevent and preferred_event.superevent !=
                self.instance) or hasattr(preferred_event,
                'superevent_preferred_for') and \
                preferred_event.superevent_preferred_for != self.instance):
                self.fail('event_assigned', graceid=preferred_event.graceid)

        return updated_attributes

    def update(self, instance, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import update_superevent

        # CurrentUserDefault doesn't work for PATCH requests since the
        # serializer has self.partial == True, the default function is never
        # called to fill empty data values. So we just grab the user directly
        # from the request.
        request = self.context.get('request', None)
        updater = getattr(request, 'user', None)
        instance = update_superevent(instance, updater, add_log_message=True,
            issue_alert=True, **validated_data)
        return instance


class SupereventEventSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'event_assigned': _('Event {graceid} is already assigned to a '
                            'Superevent'),
        'category_mismatch': _('Event {graceid} is of type \'{e_category}\', '
                               'and cannot be assigned to a superevent of '
                               'type \'{s_category}\''),
    }
    self = serializers.SerializerMethodField(read_only=True)
    event = EventGraceidField(write_only=True,
        style={'base_template': 'input.html'})
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    # Get user from request automatically
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())

    class Meta:
        model = Event
        fields = ('self', 'graceid', 'event', 'superevent', 'user')

    def get_self(self, obj):
        return api_reverse('events:event-detail', args=[obj.graceid],
            request=self.context.get('request', None))

    def validate(self, data):
        data = super(SupereventEventSerializer, self).validate(data)
        event = data.get('event')
        superevent = data.get('superevent')

        # Check if event is already assigned to a superevent
        if (event.superevent or hasattr(event, 'superevent_preferred_for')):
            self.fail('event_assigned', graceid=event.graceid)

        # Check that event has the correct type for the superevent it's being
        # assigned to
        if not superevent.event_compatible(event):
            self.fail('category_mismatch', graceid=event.graceid,
                e_category=event.get_event_category(),
                s_category=superevent.get_category_display())

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import add_event_to_superevent

        superevent = validated_data.pop('superevent')
        event = validated_data.pop('event')
        submitter = validated_data.pop('user')
        add_event_to_superevent(superevent, event, submitter,
            add_superevent_log=True, add_event_log=True,
            issue_alert=True)
        return event


class SupereventLabelSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'protected_label': _('The label \'{label}\' is managed by an automated'
                             ' process and cannot be manually added'),
        'bad_signoff_request_label': _('The \'{label}\' label cannot be '
                                       'applied to request a signoff because '
                                       'a related signoff already exists.'),
    }
    # Read only fields
    self = serializers.SerializerMethodField(read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    creator = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    # Read/write
    name = serializers.SlugRelatedField(source='label', slug_field='name',
        queryset=Label.objects.all(), required=True)
    # Write only fields (submitter used to set creator for created instance)
    submitter = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))

    class Meta:
        model = Labelling
        fields = ('self', 'name', 'created', 'creator', 'submitter',
            'superevent')

    def get_self(self, obj):
        return api_reverse('superevents:superevent-label-detail', args=[
            obj.superevent.superevent_id, obj.label.name],
            request=self.context.get('request', None))

    def validate(self, data):
        data = super(SupereventLabelSerializer, self).validate(data)
        label = data.get('label')
        superevent = data.get('superevent')

        # Don't allow protected labels to be applied
        if label.protected:
            self.fail('protected_label', label=label.name)

        # If a label exists for a signoff status, users shouldn't be
        # able to reapply the related "request signoff" label. Example:
        # ADVOK is already applied since an advocate signoff with 'OK'
        # status exists. So users shouldn't be able to apply 'ADVREQ' in
        # this case.
        req_labels = {
            'ADVREQ': ['ADVNO', 'ADVOK'],
            'H1OPS': ['H1NO', 'H1OK'],
            'L1OPS': ['L1NO', 'L1OK'],
            'V1OPS': ['V1NO', 'V1OK'],
        }
        if (label.name in req_labels and superevent.labels.filter(
            name__in=req_labels[label.name]).exists()):
            self.fail('bad_signoff_request_label', label=label.name)

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import add_label_to_superevent

        creator = validated_data.pop('submitter')
        superevent = validated_data.pop('superevent')
        label = validated_data.pop('label')
        labelling , _ = add_label_to_superevent(superevent, label, creator,
            add_log_message=True, issue_alert=True)
        return labelling


class SupereventLogSerializer(serializers.ModelSerializer):
    # Error messages
    default_error_messages = {
        'bad_display': _('There should either be as many display names as '
            'tags, or there should be no display names'),
    }
    # Read only fields
    self = serializers.SerializerMethodField(read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    issuer = serializers.SerializerMethodField(read_only=True)
    tag_names = serializers.SlugRelatedField(slug_field='name', many=True,
        source='tags', read_only=True)
    file = serializers.SerializerMethodField(read_only=True)
    # Write only fields (submitter used to set creator for created instance)
    upload = serializers.FileField(label='File', write_only=True,
        required=False)
    submitter = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    tagname = DelimitedOrListField(write_only=True, label='Tag names',
        child=serializers.CharField(), required=False)
    displayName = DelimitedOrListField(write_only=True,
        label='Display names', child=serializers.CharField(), required=False)

    class Meta:
        model = Log
        fields = ('self', 'N', 'comment', 'created', 'issuer', 'filename',
            'file_version', 'tag_names', 'submitter', 'superevent',
            'tagname', 'displayName', 'upload', 'file')

    def __init__(self, *args, **kwargs):
        super(SupereventLogSerializer, self).__init__(*args, **kwargs)
        self.fields['filename'].read_only = True
        self.fields['file_version'].read_only = True

    def get_self(self, obj):
        return api_reverse('superevents:superevent-log-detail',
            args=[obj.superevent.superevent_id, obj.N],
            request=self.context.get('request', None))

    def get_issuer(self, obj):
        # Show full name for web interface views (fetched via AJAX), unless
        # it's blank - then show username.  Outside of the web view, show the
        # username.
        request = self.context.get('request', None)
        user = obj.issuer
        if (request and request.is_ajax()):
            return (user.get_full_name() or user.get_username())
        return user.get_username()

    def get_file(self, obj):
        link = None
        if obj.filename:
            link = api_reverse('superevents:superevent-file-detail',
                args=[obj.superevent.superevent_id, obj.versioned_filename],
                request=self.context.get('request', None))
        return link

    def validate(self, data):
        data = super(SupereventLogSerializer, self).validate(data)
        tags = data.get('tagname', None)
        tag_displays = data.get('displayName', None)

        if (tags and tag_displays) and (len(tags) != len(tag_displays)):
            self.fail('bad_display')

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import create_log, get_or_create_tags

        # TODO:
        # Check user permissions here, or somewhere else? Maybe just on viewset
        # create resource

        # Convert data to be used with create_log function
        issuer = validated_data.get('submitter', None)
        superevent = validated_data.get('superevent', None)
        data_file = validated_data.get('upload', None)
        filename = getattr(data_file, 'name', "")
        tag_names = validated_data.get('tagname', [])
        display_names = validated_data.get('displayName', [])

        # Get tag objects
        tags = []
        if tag_names:
            tags = get_or_create_tags(tag_names, display_names)

        # Create log message
        log = create_log(issuer, validated_data['comment'], superevent,
            filename=filename, data_file=data_file, tags=tags,
            issue_alert=True, autogenerated=False)

        return log


class SupereventLogTagSerializer(serializers.ModelSerializer):
    """
    Note: this is a little janky due to the lack of a "through" model for
    the m2m relationship.
    """
    default_error_messages = {
        'tag_exists_for_log': _('Tag is already applied to this log message'),
    }
    parent_log = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='log',
        view_get_parent_method='get_parent_log'))
    self = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tag
        fields = ('name', 'displayName', 'self', 'parent_log')

    def get_self(self, obj):
        # NOTE: this is a little bad if this is being used to serialize an
        # object without a request or without a view being called (i.e., for
        # LVAlerts). But we don't send out LVAlerts for tags, so it's OK
        # for now.
        superevent_id = self.context['view'].kwargs.get(
            SUPEREVENT_LOOKUP_URL_KWARG)
        log_N = self.context['view'].kwargs.get('N')
        return api_reverse('superevents:superevent-log-tag-detail',
            args=[superevent_id, log_N, obj.name],
            request=self.context.get('request', None))

    def __init__(self, *args, **kwargs):
        super(SupereventLogTagSerializer, self).__init__(*args, **kwargs)
        self.fields['displayName'].label = 'Display name'
        self.fields['displayName'].help_text = ('Optional, but should be '
            'specified when creating a new tag')
        self.fields['displayName'].required = False

        # Remove unique validator from name field since we will call
        # get_or_create in the create() method
        name_validator_classes = \
            [v.__class__ for v in self.fields['name'].validators]
        uv_index = name_validator_classes.index(validators.UniqueValidator)
        self.fields['name'].validators.pop(uv_index)

    def validate(self, data):
        data = super(SupereventLogTagSerializer, self).validate(data)
        parent_log = data.get('parent_log')
        name = data.get('name')

        # Check if tag is already applied to log message
        log_tag_names = [t.name for t in parent_log.tags.all()]
        if name in log_tag_names:
            self.fail('tag_exists_for_log')

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import add_tag_to_log, get_or_create_tag

        # Get parent log message
        parent_log = validated_data.pop('parent_log')

        # get or create tag by name only
        tag = get_or_create_tag(validated_data['name'],
            validated_data.get('displayName', None))

        # Add tag to log
        add_tag_to_log(parent_log, tag, self.context.get('request').user,
            add_log_message=True, issue_alert=True)

        return tag


class SupereventVOEventSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'no_gpstime': _('Cannot build a VOEvent because preferred event does '
                        'not have a gpstime.'),
        'skymap_file_required': _('Skymap filename is required for initial '
                                  'and update VOEvents.'),
        'skymap_type_required': _('Skymap type is required for VOEvents that '
                                  'include a skymap.'),
        'skymap_not_found': _('Skymap file {filename} not found for this '
                              'superevent.'),
        'skymap_image_not_found': _('Skymap image file {filename} not found '
                                    'for this superevent.'),
    }
    # Read only fields
    issuer = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    links = serializers.SerializerMethodField(read_only=True)
    skymap_type = serializers.CharField(required=False)
    skymap_filename = serializers.CharField(required=False)
    internal = serializers.BooleanField(default=True)
    open_alert = serializers.BooleanField(default=False)
    hardware_inj = serializers.BooleanField(default=False)

    # Write only fields
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    # These fields are different for write than read because they already
    # have this silly capitalization and we can't change it without
    # breaking the client
    CoincComment = serializers.BooleanField(write_only=True, default=False)
    ProbHasNS = serializers.FloatField(write_only=True, min_value=0,
        max_value=1, required=False)
    ProbHasRemnant = serializers.FloatField(write_only=True, min_value=0,
        max_value=1, required=False)
    BNS = serializers.FloatField(write_only=True, min_value=0, max_value=1,
        required=False)
    NSBH = serializers.FloatField(write_only=True, min_value=0, max_value=1,
        required=False)
    BBH = serializers.FloatField(write_only=True, min_value=0, max_value=1,
        required=False)
    Terrestrial = serializers.FloatField(write_only=True, min_value=0,
        max_value=1, required=False)
    MassGap = serializers.FloatField(write_only=True, min_value=0,
        max_value=1, required=False)

    class Meta:
        model = VOEvent
        fields = ('voevent_type', 'file_version', 'ivorn', 'created',
            'issuer', 'filename', 'N', 'links', 'skymap_type',
            'skymap_filename', 'internal', 'open_alert', 'hardware_inj',
            'CoincComment', 'ProbHasNS', 'ProbHasRemnant', 'BNS', 'NSBH',
            'BBH', 'Terrestrial', 'MassGap', 'coinc_comment', 'prob_has_ns',
            'prob_has_remnant', 'prob_bns', 'prob_nsbh', 'prob_bbh',
            'prob_terrestrial', 'prob_mass_gap', 'superevent', 'user')

    def __init__(self, *args, **kwargs):
        super(SupereventVOEventSerializer, self).__init__(*args, **kwargs)
        read_only_fields = ['file_version', 'filename', 'ivorn',
            'coinc_comment', 'prob_has_ns', 'prob_has_remnant', 'prob_bns',
            'prob_nsbh', 'prob_bbh', 'prob_terrestrial', 'prob_mass_gap']
        for f in read_only_fields:
            self.fields.get(f).read_only = True

    def get_links(self, obj):
        file_link = None
        if obj.filename:
            file_name = "{name},{version}".format(name=obj.filename,
                version=obj.file_version)
            file_link = api_reverse('superevents:superevent-file-detail',
                args=[obj.superevent.superevent_id, file_name],
                request=self.context.get('request', None))

        link_dict = {
            'self': api_reverse('superevents:superevent-voevent-detail',
                args=[obj.superevent.superevent_id, obj.N],
                request=self.context.get('request', None)),
            'file': file_link,
        }
        return link_dict

    def validate(self, data):
        data = super(SupereventVOEventSerializer, self).validate(data)
        # Get data
        superevent = data.get('superevent')
        voevent_type = data.get('voevent_type')
        skymap_filename = data.get('skymap_filename', None)
        skymap_type = data.get('skymap_type', None)

        # Checks to do:
        # Preferred event must have gpstime
        if not superevent.preferred_event.gpstime:
            self.fail('no_gpstime')

        # initial and update VOEvents must have a skymap, and
        # preliminary VOEvents can have a skymap
        if (voevent_type in ["IN", "UP"] or
           (voevent_type == "PR" and skymap_filename != None)):

            # Check skymap filename
            if not skymap_filename:
                self.fail('skymap_file_required')

            # Check skymap type
            if not skymap_type:
                self.fail('skymap_type_required')

            # Check if skymap fits file exists
            full_skymap_path = os.path.join(superevent.datadir,
                skymap_filename)
            if not os.path.exists(full_skymap_path):
                self.fail('skymap_not_found', filename=skymap_filename)

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import create_voevent_for_superevent

        # Pop some data
        superevent = validated_data.pop('superevent')
        issuer = validated_data.pop('user')

        # Call create function - creates VOEvent object and also runs
        # buildVOEvent to create the related file.
        voevent = create_voevent_for_superevent(superevent, issuer,
            **validated_data)

        return voevent


class SupereventEMFootprintSerializer(serializers.ModelSerializer):
    """
    Should be read-only; only used as a nester serializer within
    SupereventEMObservationSerializer
    """
    start_time = serializers.DateTimeField(read_only=True,
        format=settings.GRACE_STRFTIME_FORMAT)

    class Meta:
        model = EMFootprint
        fields = ('exposure_time', 'start_time', 'N', 'raWidth', 'decWidth',
            'ra', 'dec',)


class SupereventEMObservationSerializer(serializers.ModelSerializer):
    # Error messages
    default_error_messages = {
        'list_lengths': _('ra_list, dec_list, ra_width_list, dec_width_list, '
                          'start_time_list, and duration_list must be the '
                          'same length.'),
    }
    # Read only fields
    submitter = serializers.SerializerMethodField(read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    footprint_count = serializers.SerializerMethodField(read_only=True)
    footprints = SupereventEMFootprintSerializer(many=True,
        source='emfootprint_set', read_only=True)

    # Both
    group = serializers.SlugRelatedField(slug_field='name',
        queryset=EMGroup.objects.all())

    # Write only fields
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    ra_list = DelimitedOrListField(child=serializers.FloatField(),
        write_only=True)
    dec_list = DelimitedOrListField(child=serializers.FloatField(),
        write_only=True)
    ra_width_list = DelimitedOrListField(child=serializers.FloatField(),
        write_only=True)
    dec_width_list = DelimitedOrListField(child=serializers.FloatField(),
        write_only=True)
    start_time_list = DelimitedOrListField(
        child=serializers.DateTimeField(), write_only=True)
    duration_list = DelimitedOrListField(
        child=serializers.IntegerField(min_value=0), write_only=True)

    class Meta:
        model = EMObservation
        fields = ('created', 'N', 'submitter', 'group', 'ra', 'raWidth', 'dec',
            'decWidth', 'comment','footprint_count', 'footprints', 'user',
            'superevent', 'ra_list', 'dec_list', 'ra_width_list',
            'dec_width_list', 'start_time_list', 'duration_list',)

    def __init__(self, *args, **kwargs):
        """Modify some fields"""
        super(SupereventEMObservationSerializer, self).__init__(*args, **kwargs)
        self.fields['ra'].read_only = True
        self.fields['raWidth'].read_only = True
        self.fields['dec'].read_only = True
        self.fields['decWidth'].read_only = True

    def get_footprint_count(self, obj):
        return obj.emfootprint_set.count()

    def get_submitter(self, obj):
        # Show full name for web interface views (fetched via AJAX), unless
        # it's blank - then show username.  Outside of the web view, show the
        # username.
        request = self.context.get('request', None)
        user = obj.submitter
        if (request and request.is_ajax()):
            return (user.get_full_name() or user.get_username())
        return user.get_username()

    def validate(self, data):
        data = super(SupereventEMObservationSerializer, self).validate(data)
        ra_list = data.get('ra_list')
        dec_list = data.get('dec_list')
        ra_width_list = data.get('ra_width_list')
        dec_width_list = data.get('dec_width_list')
        start_time_list = data.get('start_time_list')
        duration_list = data.get('duration_list')

        # Make sure that all lists have the same length
        list_length = len(ra_list)
        all_lists = (ra_list, dec_list, ra_width_list, dec_width_list,
            start_time_list, duration_list)
        if not all(map(lambda l: len(l) == list_length, all_lists)):
            self.fail('list_lengths')

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import create_emobservation_for_superevent

        # Create EMObservation and EMFootprint set
        emo = create_emobservation_for_superevent(validated_data['superevent'],
            validated_data['user'], validated_data['ra_list'],
            validated_data['dec_list'], validated_data['ra_width_list'],
            validated_data['dec_width_list'], validated_data['start_time_list'],
            validated_data['duration_list'], validated_data['group'],
            validated_data['comment'])

        return emo


class SupereventSignoffSerializer(serializers.ModelSerializer):
    # Error messages
    default_error_messages = {
        'label_missing': _('{s_type} signoff not requested for superevent '
                           '{id}: label \'{label}\' not present.'),
        'instrument_missing': _('Operator signoffs require an instrument'),
        'instrument_provided': _('Advocate signoffs are not relevant to a'
                                 'particular instrument; do not provide one.'),
        'bad_update': _('Request would not modify the signoff.')
    }
    signoff_type = serializers.ChoiceField(required=True,
        choices=Signoff.SIGNOFF_TYPE_CHOICES)
    self = serializers.SerializerMethodField(read_only=True)
    submitter = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())

    class Meta:
        model = Signoff
        fields = ['self', 'signoff_type', 'instrument', 'status', 'submitter',
            'comment', 'superevent', 'user']

    def get_self(self, obj):
        return api_reverse('superevents:superevent-signoff-detail', args=[
            obj.superevent.superevent_id, obj.signoff_type + obj.instrument],
            request=self.context.get('request', None))

    def validate(self, data):
        data = super(SupereventSignoffSerializer, self).validate(data)
        instrument = data.get('instrument')
        superevent = data.get('superevent')
        signoff_type = data.get('signoff_type')

        # Fail if instrument not provided for operator signoff
        if (signoff_type == Signoff.SIGNOFF_TYPE_OPERATOR and
            not instrument):
            self.fail('instrument_missing')

        # Fail if instrument provided for advocate signoff
        if (signoff_type == Signoff.SIGNOFF_TYPE_ADVOCATE and
            instrument != ''):
            self.fail('instrument_provided')

        # A few method-specific validation checks: this way we don't
        # have to have multiple serializers
        http_method = self.context.get('request').method

        # If superevent doesn't have expected label, fail
        # (POST requests only; for PUT/PATCH we don't want to check this
        # since we are updating an already existing signoff)
        if (http_method == 'POST'):
            # Get expected label
            if (instrument == ""):
                expected_label = 'ADVREQ'
            else:
                expected_label = instrument + 'OPS'
            if not expected_label in [l.name for l in superevent.labels.all()]:
                self.fail('label_missing', s_type=signoff_type,
                    label=expected_label, id=superevent.superevent_id)

        if (http_method in ['PUT', 'PATCH']):
            comment = data.get('comment')
            status = data.get('status')
            if (comment == self.instance.comment and
                status == self.instance.status):
                self.fail('bad_update')

        return data

    def create(self, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import create_signoff

        return create_signoff(validated_data['superevent'],
            validated_data['user'], validated_data['signoff_type'],
            validated_data['instrument'], validated_data['status'],
            validated_data['comment'], add_log_message=True, issue_alert=True)

    def update(self, instance, validated_data):
        # Function-level import to prevent circular import in alerts
        from superevents.utils import update_signoff
        # Pull data out from the validated_data dictionary since the
        # update_signoff function has non-kwargs for most of the args.
        updater = validated_data.get('user')
        status = validated_data.get('status')
        comment = validated_data.get('comment')

        # CurrentUserDefault doesn't work for PATCH requests since the
        # serializer has self.partial == True, the default function is never
        # called to fill empty data values. So we just grab the user directly
        # from the request.
        request = self.context.get('request')
        if request.method == "PATCH":
            updater = getattr(request, 'user')

        # Call update_signoff
        instance = update_signoff(instance, updater, status, comment,
            add_log_message = True, issue_alert=True)
        return instance


class SupereventGroupObjectPermissionSerializer(serializers.ModelSerializer):
    group = serializers.SlugRelatedField(slug_field='name',
        read_only=True)
    permission = serializers.SlugRelatedField(slug_field=
        'codename', read_only=True)

    class Meta:
        model = SupereventGroupObjectPermission
        fields = ['group', 'permission']
