from __future__ import absolute_import
import logging

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from guardian.models import GroupObjectPermission

from core.urls import build_absolute_uri
from events.shortcuts import is_event
from events.view_utils import eventToDict, eventLogToDict, signoffToDict, \
    emObservationToDict, embbEventLogToDict, groupeventpermissionToDict, \
    labelToDict, voeventToDict
from ..main import issue_alerts
from ..utils import AlertIssuerWithParentObject

# Set up logger
logger = logging.getLogger(__name__)


# NOTE: we have to be careful in all of these serializers since we want to
# serialize the event subclass always, not the base event object.
class AlertIssuerWithParentEvent(AlertIssuerWithParentObject):
    parent_serializer_class = staticmethod(eventToDict)

    def serialize_obj(self):
        return self.serializer_class(self.obj)

    def serialize_parent(self):
        return self.parent_serializer_class(self.get_parent_obj(),
            is_alert=True)

    def _get_parent_obj(self):
        # Assumes that the obj has a direct relation to an event
        if not hasattr(self.obj, 'event'):
            raise AttributeError(('object of class {0} does not have a direct '
                'relationship to an event').format(
                self.obj.__class__.__name__))
        # Make sure we have the event "subclass"
        return self.obj.event.get_subclass_or_self()

    def issue_alerts(self):
        issue_alerts(self.get_parent_obj(), self.alert_type,
           self.serialize_obj(), self.serialize_parent())


class EventAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(eventToDict)
    alert_types = ['new', 'update', 'selected_as_preferred',
        'removed_as_preferred', 'added_to_superevent',
        'removed_from_superevent']

    def serialize_obj(self):
        return self.serializer_class(self.obj.get_subclass_or_self(),
            is_alert=True)

    def _get_parent_obj(self):
        return self.obj.get_subclass_or_self()


class EventLogAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(eventLogToDict)
    alert_types = ['log']


class EventLabelAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(labelToDict)
    alert_types = ['label_added', 'label_removed']

    def issue_alerts(self):
        issue_alerts(self.get_parent_obj(), self.alert_type,
            self.serialize_obj(), self.serialize_parent(),
            label=self.obj.label)


class EventVOEventAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(voeventToDict)
    alert_types = ['voevent']


class EventEMObservationAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(emObservationToDict)
    alert_types = ['emobservation']


class EventEMBBEventLogAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(embbEventLogToDict)
    alert_types = ['embb_event_log']


class EventSignoffAlertIssuer(AlertIssuerWithParentEvent):
    serializer_class = staticmethod(signoffToDict)
    alert_types = ['signoff_created', 'signoff_updated', 'signoff_deleted']


class EventPermissionsAlertIssuer(EventAlertIssuer):
    serializer_class = staticmethod(groupeventpermissionToDict)
    alert_types = ['exposed', 'hidden']

    def serialize_obj(self):
        """self.obj should be an event here"""
        gops = GroupObjectPermission.objects.filter(
            object_pk=self.obj.pk,
            content_type=ContentType.objects.get_for_model(self.obj))
        gop_list = [self.serializer_class(gop) for gop in gops]
        return gop_list
