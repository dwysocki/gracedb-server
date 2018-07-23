from __future__ import absolute_import
import logging

from django.contrib.auth import get_user_model

from rest_framework import serializers

from events.models import Event

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


class GenericField(serializers.Field):
    # Field, property, or callable of the object which will be used to
    # generate the representation of the object.
    to_repr = None
    lookup_field = 'id'
    model = None

    def __init__(self, *args, **kwargs):
        self.to_repr = kwargs.pop('to_repr', self.to_repr)
        self.lookup_field = kwargs.pop('lookup_field', self.lookup_field)
        self.model = kwargs.pop('model', self.model)

        assert self.to_repr is not None, ('Must specify to_repr')
        assert self.model is not None, ('Must specify model')
        super(GenericField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        value = getattr(obj, self.to_repr)

        # Handle case where we are given a function instead of
        # a model field or a property
        if callable(value):
            value = value()
        return value

    def to_internal_value(self, data):
        model_dict = self.get_model_dict(data)
        try:
            return self.model.objects.get(**model_dict)
        except self.model.DoesNotExist:
            error_msg = '{model} with {lf}={data} does not exist' \
                .format(model=self.model.__name__, lf=model_dict.keys()[0],
                data=model_dict.values()[0])
            raise serializers.ValidationError(error_msg)

    def get_model_dict(self, data):
        return {self.lookup_field: data}


class EventGraceidField(GenericField, serializers.RelatedField):
    to_repr = 'graceid'
    lookup_field = 'id'
    model = Event
    queryset = Event.objects.all()

    def get_model_dict(self, data):
        return {self.lookup_field: data[1:]}
