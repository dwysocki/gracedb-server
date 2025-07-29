from __future__ import absolute_import
import functools
import logging
import os
import json
import numbers

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_framework import fields, serializers, validators
from rest_framework.exceptions import ValidationError

from gwtc.models import gwtc_catalog, gwtc_gevent, gwtc_superevent, \
    dot_slug_validator
from superevents.models import Superevent
from events.models import Event, Pipeline

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)

# some variables:
PIPELINE_KEY = 'pipelines'

class gwtc_serializer(serializers.ModelSerializer):
    number = serializers.CharField(required=True, allow_null=False,
        allow_blank=False, validators=[dot_slug_validator])
    smap = serializers.JSONField(required=True, write_only=True, allow_null=False)
    version = serializers.ReadOnlyField()
    comment = serializers.CharField(allow_blank=True, allow_null=True, required=False)
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
                  'smap', 'user', 'gwtc_superevents', 'comment')

    # Make sure the comment is a blank and not null:
    def validate_comment(self, value):
        if not value:
           return ''
        else:
           return value

    # Look at the smap json. Perform checks such as verifying that superevents
    # are in the database, and that events are part of that superevent.
    def validate_smap(self, value):
        for sevent, sevent_dict in value.items():
            # first try and get the superevent:
            try:
               s = Superevent.get_by_date_id(sevent)
            except (ObjectDoesNotExist, Superevent.DateIdError):
               raise serializers.ValidationError(f'Superevent {sevent} '
                           'was not found in the database.')

            # validate the per-pipeline events dictionary:
            try:
                events_dict = sevent_dict[PIPELINE_KEY]

                if isinstance(events_dict, dict):
                    # Now loop over the events and pipelines that are part of that superevent:
                    for pipeline, event in events_dict.items():
                        # see if the event exists:
                        try:
                            e = Event.getByGraceid(event)
        
                            # ensure that we have the base event class:
                            if hasattr(e, 'event_ptr'):
                               e = e.event_ptr
        
                        except ObjectDoesNotExist:
                            raise serializers.ValidationError(f'Catalog Error: Event {event} '
                                   'was not found in the database.')

                        except Exception:
                            raise serializers.ValidationError(f'Unable to parse event {event}')
        
                        # now, see if the event actually is part of the superevent:
                        if not e in s.events.all():
                            raise serializers.ValidationError(f'Catalog Error: Event {event} '
                                   f'is not part of superevent {sevent}.')
        
                        # now see if the event's pipeline matches up with what is provided.
                        if not e.pipeline.name == pipeline:
                            raise serializers.ValidationError('Catalog Error: '
                                   f'Pipeline of {event} ({e.pipeline.name}) '
                                   f'does not match the supplied pipeline ({pipeline})')
                else:
                    raise serializers.ValidationError('value corresponding to '
                           f'{sevent}["{PIPELINE_KEY}"] is not a dictionary')

            except KeyError:
                raise serializers.ValidationError('superevent key '
                       f'{PIPELINE_KEY} not found for gwtc_superevent '
                       f'{sevent}.')

            # test far:
            try:
               far = sevent_dict['far']

               if far and not isinstance(far, numbers.Number):
                   raise serializers.ValidationError('far value for '
                         f'{sevent} must be null or a valid number, not '
                         f'{far}')
               
            except KeyError:
               raise serializers.ValidationError('far not found for '
                      f'superevent {sevent}')

            # test pastro:
            try:
               pastro = sevent_dict['pastro']

               if pastro and not isinstance(pastro, dict):
                   raise serializers.ValidationError('pastro value for '
                         f'{sevent} must be null or a valid dictionary, not '
                         f'{pastro}')
               
            except KeyError:
               raise serializers.ValidationError('pastro not found for '
                      f'superevent {sevent}')
            

        # I think that's good? so return the validated data
        return value

    def validate(self, data):
        data = super(gwtc_serializer, self).validate(data)
        return data

    def create(self, validated_data):
        # This is the routine that creates the catalog object, the catalog superevents,
        # and catalog events.

        # First, create the catalog object:
        new_gwtc = gwtc_catalog.objects.create(number=validated_data.pop('number'),
                                submitter=validated_data.pop('user'),
                                comment=validated_data.pop('comment', ''))
 
        # Similar to the validation step, loop over the superevents and events and then
        # add them to the catalog.
        
        catalog_map = validated_data.pop('smap')

        for sevent, sevent_dict in catalog_map.items():

            # Get the superevent, create the gwtc superevent

            s = Superevent.get_by_date_id(sevent)
            new_gwtc_superevent = gwtc_superevent.objects.create(
                                        superevent = s,
                                        gwtc_catalog = new_gwtc,
                                        far=sevent_dict['far'],
                                        pastro=sevent_dict['pastro'])


            # Get the per-pipeline events:
            pipeline_events = sevent_dict.pop(PIPELINE_KEY)

            # Now create the events. It would be more efficient to pre-fetch the pipelines,
            # but whatever.
            for pipeline, event in pipeline_events.items():
                new_gwtc_event = gwtc_gevent.objects.create(
                                      gwtc_catalog = new_gwtc,
                                      gwtc_superevent = new_gwtc_superevent,
                                      gevent = Event.getByGraceid(event),
                                      pipeline = Pipeline.objects.get(name=pipeline))

        return new_gwtc

    # Populate custom fields.
    def get_gwtc_superevents(self, obj):

        return {se.superevent.superevent_id: 
                   {
                     'pipelines': {e.gevent.pipeline.name: e.gevent.graceid 
                                   for e in se.gwtc_gevent_set.all()},
                     'far': se.far,
                     'pastro': se.pastro,
                   }
                for se in obj.gwtc_superevent_set.all()}
