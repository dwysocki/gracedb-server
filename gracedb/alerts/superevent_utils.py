from django.urls import reverse
from rest_framework.renderers import JSONRenderer

from .main import issue_alerts
from core.urls import build_absolute_uri
from superevents.api.serializers import SupereventSerializer, \
    SupereventLogSerializer, SupereventLabelSerializer, \
    SupereventEMObservationSerializer
from superevents.shortcuts import is_superevent

import logging
logger = logging.getLogger(__name__)


def superevent_alert_helper(obj, serializer=SupereventSerializer,
    request=None):
    """
    Assume non-superevent objects passed to this function have a
    foreign key link to a superevent
    """

    # If superevent_id is None, assume obj is a Superevent
    if is_superevent(obj):
        superevent_id = obj.superevent_id
    else:
        try:
            superevent_id = obj.superevent.superevent_id
        except:
            # TODO: raise appropriate error
            pass

    # Construct URL for web view
    url = build_absolute_uri(reverse('superevents:view', args=[superevent_id]),
        request)

    # Serialize the object into a dictionary
    obj_dict = serializer(obj).data

    return url, obj_dict


def issue_alert_for_superevent_creation(superevent, request=None):

    # Get URL and serialized superevent
    url, serialized_object = superevent_alert_helper(superevent,
        request=request)

    # Description
    description = "NEW: superevent {0}".format(superevent.superevent_id)

    # Send alerts
    issue_alerts(superevent, alert_type="new", url=url,
        description=description, serialized_object=serialized_object)


#def issue_alert_for_superevent_update(superevent, request=None):
#    # Get URL and serialized superevent
#    url, serialized_object = superevent_alert_helper(superevent,
#        request=request)
#
#    # Description
#    # TODO: fix
#    description = "UPDATE: superevent {0}".format(superevent.superevent_id)
#
#    # Send alerts
#    issue_alerts(superevent, alert_type="update", url=url,
#        description=description, serialized_object=serialized_object)


def issue_alert_for_superevent_log(log, request=None):

    # Get URL for superevent webview and serialized log
    url, serialized_object = superevent_alert_helper(log,
        SupereventLogSerializer, request=request)

    # Description
    if log.filename:
        description = "UPLOAD: '{filename}'".format(filename=log.filename)
    else:
        description = "LOG:"
    description += " {message}".format(message=log.comment)

    # Send alerts
    issue_alerts(log.superevent, alert_type="update", url=url,
        description=description, serialized_object=serialized_object,
        file_name=log.filename)


def issue_alert_for_superevent_label_creation(labelling, request=None):

    # Get URL for superevent webview and serialized label
    url, serialized_object = superevent_alert_helper(labelling,
        SupereventLabelSerializer, request=request)

    # Description
    description = "LABEL: {label} added".format(label=labelling.label.name)

    # Send alerts
    # NOTE: current alerts don't include an object (change this?)
    issue_alerts(labelling.superevent, alert_type="label", url=url,
        description=description, serialized_object=None)


def issue_alert_for_superevent_label_removal(labelling, request=None):
    # Get URL for superevent webview and serialized label
    url, serialized_object = superevent_alert_helper(labelling,
        SupereventLabelSerializer, request=request)

    # Description
    description = "UPDATE: {label} removed".format(label=labelling.label.name)

    # Send alerts
    # TODO: should this be a 'label' alert or an 'update' alert
    issue_alerts(labelling.superevent, alert_type="update", url=url,
        description=description, serialized_object=None)


def issue_alert_for_superevent_voevent(voevent, request=None):
    pass


def issue_alert_for_superevent_emobservation(emobservation, request=None):
    # Get URL for superevent webview and serialized label
    url, serialized_object = superevent_alert_helper(emobservation,
        SupereventEMObservationSerializer, request=request)

    # Description
    description = "New EMBB observation record for {group}".format(
        group=emobservation.group.name)

    # Send alerts
    issue_alerts(emobservation.superevent, alert_type="update", url=url,
        description=description, serialized_object=serialized_object)
