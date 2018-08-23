from __future__ import absolute_import
import logging

from rest_framework import serializers

from events.models import Event
from ..fields import GenericField

# Set up logger
logger = logging.getLogger(__name__)


class EventGraceidField(GenericField, serializers.RelatedField):
    to_repr = 'graceid'
    lookup_field = 'id'
    model = Event
    queryset = Event.objects.all()

    def get_model_dict(self, data):
        return {self.lookup_field: data[1:]}
