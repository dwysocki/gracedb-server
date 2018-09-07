from __future__ import absolute_import
import logging

from django.urls import reverse

from core.urls import build_absolute_uri
from events.shortcuts import is_event
from events.view_utils import eventToDict, eventLogToDict
from ..main import issue_alerts

# Set up logger
logger = logging.getLogger(__name__)


def event_alert_helper(obj, serializer=eventToDict, request=None):
    """
    If obj is not an event, assume it is an object with a relation to
    an Event object.
    """

    # If superevent_id is None, assume obj is a Superevent
    if is_event(obj):
        graceid = event.graceid()
    else:
        try:
            graceid = obj.event.graceid()
        except:
            # TODO: raise appropriate error
            pass

    # Construct URL for web view
    url = build_absolute_uri(reverse('view', args=[graceid]), request)

    # Serialize the object into a dictionary
    obj_dict = serializer(obj)

    return url, obj_dict


def issue_alert_for_event_log(log, request=None):

    # Get URL for event webview and serialized log
    url, serialized_object = event_alert_helper(log, eventLogToDict, request)

    # Description
    if log.filename:
        description = "UPLOAD: '{filename}'".format(filename=log.filename)
    else:
        description = "LOG:"
    description += " {message}".format(message=log.comment)

    # Send alerts
    issue_alerts(log.event, alert_type="update", url=url,
        description=description, serialized_object=serialized_object,
        file_name=log.filename)

