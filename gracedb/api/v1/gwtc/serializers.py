from __future__ import absolute_import
import functools
import logging
import os
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_framework import fields, serializers, validators
from rest_framework.exceptions import ValidationError

from gwtc.models import gwtc_catalog, gwtc_gevent, gwtc_superevent
from superevents.models import Superevent
from events.models import Event, Pipeline

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)

class gwtc_serializer(serializers.ModelSerializer):
    number = serializers.SlugField(required=True, allow_null=False, allow_blank=False)
    smap = serializers.JSONField(required=True, write_only=True, allow_null=False)
    version = serializers.ReadOnlyField()
    # Get user from request automatically
    user = serializers.HiddenField(write_only=True,
        default=serializers.CurrentUserDefault())
    submitter = serializers.SlugRelatedField(slug_field='username',
        read_only=True)
    created = serializers.DateTimeField(format=settings.GRACE_STRFTIME_FORMAT,
        read_only=True)

    # Custom display fields. These are read-only fields for displaying/GET'ing
    # with the API:
    gwtc_superevents = serializers.SerializerMethodField(read_only=True)


    class Meta:
        model = gwtc_catalog
        fields = ('number', 'version', 'created', 'submitter', 
                  'smap', 'user', 'gwtc_superevents')

    # Look at the smap json. Perform checks such as verifying that superevents
    # are in the database, and that events are part of that superevent.
    def validate_smap(self, value):
        for sevent, events in value.items():
            # first try and get the superevent:
            try:
               s = Superevent.get_by_date_id(sevent)
            except (ObjectDoesNotExist, Superevent.DateIdError):
               raise serializers.ValidationError(f'Superevent {sevent} '
                           'was not found in the database.')

            # Now loop over the events and pipelines that are part of that superevent:
            for pipeline, event in events.items():
                # see if the event exists:
                try:
                    e = Event.getByGraceid(event)

                    # ensure that we have the base event class:
                    if hasattr(e, 'event_ptr'):
                       e = e.event_ptr

                except ObjectDoesNotExist:
                    raise serializers.ValidationError(f'Catalog Error: Event {event} '
                           'was not found in the database.')

                # now, see if the event actually is part of the superevent:
                if not e in s.events.all():
                    raise serializers.ValidationError(f'Catalog Error: Event {event} '
                           f'is not part of superevent {sevent}.')

                # now see if the event's pipeline matches up with what is provided.
                if not e.pipeline.name == pipeline:
                    raise serializers.ValidationError('Catalog Error: '
                           f'Pipeline of {event} ({e.pipeline.name}) '
                           f'does not match the supplied pipeline ({pipeline})')

        # I think that's good? so return the validated data
        return value

    def validate(self, data):
        data = super(gwtc_serializer, self).validate(data)
        return data

    def create(self, validated_data):
        # This is the routine that creates the catalog object, the catalog superevents,
        # and catalog events.

        # First, create the catalog object:
        new_gwtc = gwtc_catalog.objects.create(number = validated_data.pop('number'),
                                submitter = validated_data.pop('user'))
 
        # Similar to the validation step, loop over the superevents and events and then
        # add them to the catalog.
        
        catalog_map = validated_data.pop('smap')

        for sevent, events in catalog_map.items():

            # Get the superevent, create the gwtc superevent
            s = Superevent.get_by_date_id(sevent)
            new_gwtc_superevent = gwtc_superevent.objects.create(
                                        superevent = s,
                                        gwtc_catalog = new_gwtc)

            # Now create the events. It would be more efficient to pre-fetch the pipelines,
            # but whatever.
            for pipeline, event in events.items():
                new_gwtc_event = gwtc_gevent.objects.create(
                                      gwtc_catalog = new_gwtc,
                                      gwtc_superevent = new_gwtc_superevent,
                                      gevent = Event.getByGraceid(event),
                                      pipeline = Pipeline.objects.get(name=pipeline))

        return new_gwtc

    # Populate custom fields.
    def get_gwtc_superevents(self, obj):

        return {se.superevent.superevent_id: {e.gevent.pipeline.name: e.gevent.graceid 
                                                 for e in se.gwtc_gevent_set.all()}
                   for se in obj.gwtc_superevent_set.all()}
