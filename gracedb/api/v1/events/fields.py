from __future__ import absolute_import
import logging
import six

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from events.models import Event
from ..fields import GenericField

# Set up logger
logger = logging.getLogger(__name__)


class EventGraceidField(GenericField, serializers.RelatedField):
    default_error_messages = {
        'invalid': _('Event graceid must be a string.'),
        'bad_graceid': _('Not a valid graceid.'),
    }
    trim_whitespace = True
    to_repr = 'graceid'
    lookup_field = 'pk'
    model = Event
    queryset = Event.objects.all()

    def _validate_graceid(self, data):
        # data should be a string at this point
        prefix = data[0]
        suffix = data[1:]
        if not prefix in 'GEHMT':
            self.fail('bad_graceid')
        try:
            suffix = int(suffix)
        except ValueError:
            self.fail('bad_graceid')

    def to_internal_value(self, data):
        # Add string validation
        if not isinstance(data, six.string_types):
            self.fail('invalid')
        value = six.text_type(data)
        if self.trim_whitespace:
            value = value.strip()

        # Convert to uppercase (allows g1234 to work)
        value = value.upper()

        # Graceid validation
        self._validate_graceid(value)

        return super(EventGraceidField, self).to_internal_value(value)

    def get_model_dict(self, data):
        return {self.lookup_field: data[1:]}

    def get_does_not_exist_error(self, graceid):
        err_msg = "Event with graceid {graceid} does not exist.".format(
            graceid=graceid)
        return err_msg
