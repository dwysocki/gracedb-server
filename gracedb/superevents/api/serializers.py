from rest_framework import serializers, validators
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from ..models import Superevent, Labelling, Log, VOEvent, EMObservation
from ..forms import LogCreateForm
from ..utils import create_superevent, update_superevent, add_tag_to_log, \
    create_log, add_event_to_superevent, add_label_to_superevent, \
    get_or_create_tag, get_or_create_tags

from .fields import ParentObjectDefault
from .settings import SUPEREVENT_LOOKUP_FIELD

from events.models import Event, Label, Tag, EMGroup
from events.view_utils import reverse as gracedb_reverse
from events.api.fields import EventGraceidField

UserModel = get_user_model()

import functools
import logging
logger = logging.getLogger(__name__)


class SupereventSerializer(serializers.ModelSerializer):
    # Error messages
    default_error_messages = {
        'event_assigned': _('Event {graceid} is already assigned to a '
                            'Superevent'),
    }

    # Fields
    submitter = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    preferred_event = EventGraceidField(required=True)
    created = serializers.DateTimeField(source='date_created',
        format=settings.GRACE_STRFTIME_FORMAT, read_only=True)
    # Add custom fields
    gw_events = serializers.SerializerMethodField(read_only=True)
    em_events = serializers.SerializerMethodField(read_only=True)
    links = serializers.SerializerMethodField(read_only=True)
    labels = serializers.SlugRelatedField(slug_field='name', many=True,
        queryset=Label.objects.all(), required=False)
    # Write only fields (user field is used to set submitter for instance
    # creation)
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    events = EventGraceidField(many=True, required=False, write_only=True)

    class Meta:
        model = Superevent
        fields = ('superevent_id', 'created', 'submitter', 'preferred_event',
            'events', 't_start', 't_0', 't_end', 'gw_events', 'em_events',
            'labels', 'links', 'user')

    def validate(self, data):
        data = super(SupereventSerializer, self).validate(data)
        preferred_event = data.get('preferred_event')
        events = data.get('events')

        # Make sure preferred_event is not already assigned
        if preferred_event:
            if (preferred_event.superevent or hasattr(preferred_event,
                'superevent_preferred_for')):
                self.fail('event_assigned', graceid=preferred_event.graceid())

        # Make sure the events are not already assigned to a superevent
        if events:
            for ev in events:
                if (ev.superevent or hasattr(ev, 'superevent_preferred_for')):
                    self.fail('event_assigned', graceid=ev.graceid())

        return data

    def create(self, validated_data):
        submitter = validated_data.pop('user')

        # TODO: 
        # Check user permissions here, or somewhere else? Maybe just on viewset
        # create resource
        return create_superevent(submitter, **validated_data)

    # Custom method fields ----------------------------------------------------
    def get_gw_events(self, obj):
        return [ev.graceid() for ev in obj.get_internal_events()]

    def get_em_events(self, obj):
        return [ev.graceid() for ev in obj.get_external_events()]

    def get_links(self, obj):
        bound_reverse = functools.partial(gracedb_reverse,
            args=[obj.superevent_id], request=self.context['request'])
        link_dict = {
            'events': bound_reverse('superevent-event-list'),
            'labels': bound_reverse('superevent-label-list'),
            'logs': bound_reverse('superevent-log-list'),
            'files': bound_reverse('superevent-file-list'),
            'self': bound_reverse('superevent-detail'),
            'voevents': bound_reverse('superevent-voevent-list'),
            'emobservations': bound_reverse('superevent-emobservation-list'),
        }
        return link_dict


class SupereventUpdateSerializer(SupereventSerializer):
    """
    Used for updates ONLY (PUT/PATCH). Overrides validation which is needed
    for object creation.
    """

    def __init__(self, *args, **kwargs):
        super(SupereventUpdateSerializer, self).__init__(*args, **kwargs)
        self.fields['events'].read_only = True
        self.fields['labels'].read_only = True

    def validate(self, data):
        # We don't want to use the SupereventSerializers validate method, which
        # is why we use that class in the super() call here
        data = super(SupereventSerializer, self).validate(data)
        preferred_event = data.get('preferred_event')

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
                self.fail('event_assigned', graceid=preferred_event.graceid())

        return data

    def update(self, instance, validated_data):
        # CurrentUserDefault doesn't work for PATCH requests since the
        # serializer has self.partial == True, the default function is never
        # called to fill empty data values. So we just grab the user directly
        # from the request.
        updater = self.context['request'].user
        instance = update_superevent(instance, updater, issue_alert=True,
            **validated_data)
        return instance


class SupereventEventSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'event_assigned': _('Event {graceid} is already assigned to a '
                            'Superevent'),
    }
    self = serializers.SerializerMethodField(read_only=True)
    event = EventGraceidField(write_only=True)
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    # Get user from request automatically
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())

    class Meta:
        model = Event
        fields = ('self', 'graceid', 'event', 'superevent', 'user')

    def get_self(self, obj):
        return gracedb_reverse('event-detail', args=[obj.graceid()],
            request=self.context['request'])

    def validate(self, data):
        data = super(SupereventEventSerializer, self).validate(data)
        event = data.get('event', None)
        if (event.superevent or hasattr(event, 'superevent_preferred_for')):
            self.fail('event_assigned', graceid=event.graceid())
        return data

    def create(self, validated_data):
        superevent = validated_data.pop('superevent')
        event = validated_data.pop('event')
        submitter = validated_data.pop('user')
        add_event_to_superevent(superevent, event, submitter,
            add_superevent_log=True, add_event_log=True,
            issue_superevent_alert=True, issue_event_alert=True)
        return event


class SupereventLabelSerializer(serializers.ModelSerializer):
    # Read only fields
    self = serializers.SerializerMethodField(read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    creator = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    # Read/write
    name = serializers.SlugRelatedField(source='label', slug_field='name',
        queryset=Label.objects.all())
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
        superevent_id = self.context['view'].kwargs.get(
            SUPEREVENT_LOOKUP_FIELD)
        return gracedb_reverse('superevent-label-detail', args=[
            superevent_id, obj.label.name], request=self.context['request'])

    def create(self, validated_data):
        creator = validated_data.pop('submitter')
        superevent = validated_data.pop('superevent')
        label = validated_data.pop('label')
        labelling = add_label_to_superevent(superevent, label, creator,
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
    issuer = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    tag_names = serializers.SlugRelatedField(slug_field='name', many=True,
        source='tags', read_only=True)
    # Write only fields (submitter used to set creator for created instance)
    upload = serializers.FileField(label='File', write_only=True,
        required=False)
    submitter = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    superevent = serializers.HiddenField(write_only=True,
        default=ParentObjectDefault(context_key='superevent'))
    tagname = serializers.ListField(write_only=True, label='Tag names',
        child=serializers.CharField(), required=False)
    displayName = serializers.ListField(write_only=True, label='Display names',
        child=serializers.CharField(), required=False)

    class Meta:
        model = Log
        fields = ('self', 'N', 'comment', 'created', 'issuer', 'filename',
            'file_version', 'tag_names', 'submitter', 'superevent',
            'tagname', 'displayName', 'upload')

    def __init__(self, *args, **kwargs):
        super(SupereventLogSerializer, self).__init__(*args, **kwargs)
        self.fields['filename'].read_only = True
        self.fields['file_version'].read_only = True

    def get_self(self, obj):
        superevent_id = self.context['view'].kwargs.get(
            SUPEREVENT_LOOKUP_FIELD)
        return gracedb_reverse('superevent-log-detail', args=[
            superevent_id, obj.N], request=self.context['request'])

    def validate(self, data):
        data = super(SupereventLogSerializer, self).validate(data)
        tags = data.get('tagname', None)
        tag_displays = data.get('displayName', None)

        if (tags and tag_displays) and (len(tags) != len(tag_displays)):
            self.fail('bad_display')

        return data

    def create(self, validated_data):
        # Check user permissions here, or somewhere else? Maybe just on viewset
        # create resource
        logger.debug(validated_data)

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
        superevent_id = self.context['view'].kwargs.get(
            SUPEREVENT_LOOKUP_FIELD)
        log_N = self.context['view'].kwargs.get('N')
        return gracedb_reverse('superevent-log-tag-detail', args=[
            superevent_id, log_N, obj.name], request=self.context['request'])

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
    # Read only fields
    issuer = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    links = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VOEvent
        fields = ('voevent_type', 'file_version', 'ivorn', 'created',
            'issuer', 'filename', 'N', 'links')

    def get_links(self, obj):
        file_link = None
        if obj.filename:
            file_name = "{name},{version}".format(obj.filename, 
                obj.file_version)
            file_link = gracedb_reverse('superevent-file-detail', args=[
                obj.superevent.superevent_id, file_name],
                request=self.context['request']),

        link_dict = {
            'self': gracedb_reverse('superevent-voevent-detail', args=[
                obj.superevent.superevent_id, obj.N],
                request=self.context['request']),
            'file': file_link
        }
        return link_dict

    # TODO:
    # VOEvent creation!!


class SupereventEMObservationSerializer(serializers.ModelSerializer):
    # Read only fields
    submitter = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)
    footprint_count = serializers.SerializerMethodField(read_only=True)
    footprints = serializers.SerializerMethodField(read_only=True)

    # Both
    group = serializers.SlugRelatedField(slug_field='name',
        queryset=EMGroup.objects.all())

    # Write only fields
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())

    class Meta:
        model = EMObservation
        fields = ('created', 'N', 'submitter', 'group', 'ra', 'raWidth', 'dec',
            'decWidth', 'footprint_count', 'footprints', 'user')

    def get_footprint_count(self, obj):
        return obj.emfootprint_set.count()

    def get_footprints(self, obj):
        return [{
            'exposure_time': fp.exposure_time,
            'start_time': fp.start_time.strftime(
                settings.GRACE_STRFTIME_FORMAT),
            'N': fp.N,
            'raWidth': fp.raWidth,
            'decWidth': fp.decWidth,
            'ra': fp.ra,
            'dec': fp.dec,
        } for fp in obj.emfootprint_set.all().order_by('-N')]
        return 'test'

    # TODO:
    # EMObservation creation!!
