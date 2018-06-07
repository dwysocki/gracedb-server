
import simplejson
import os
import socket
import sys


from django.core.mail import EmailMessage
from django.conf import settings

from .lvalert import send_with_lvalert_overseer, send_with_lvalert_send
from core.time_utils import gpsToUtc
from events.permission_utils import is_external
from events.query import filter_for_labels
from events.shortcuts import is_event
from superevents.shortcuts import is_superevent

import logging
logger = logging.getLogger(__name__)

if settings.USE_LVALERT_OVERSEER:
    from hashlib import sha1
    from multiprocessing import Manager


def get_xmpp_node_names(event_or_superevent):
    """
    Utility function for determining the names of nodes to which XMPP
    notifications should be sent. Accepts an event or superevent object as the
    sole argument.
    """

    # Compile a list of node names
    node_names = []
    if is_superevent(event_or_superevent):
        # TODO: test superevents
        is_test = False
        if is_test:
            superevent_node = 'test_superevent'
        else:
            superevent_node = 'superevent'
        node_names.append(superevent_node)
    elif is_event(event_or_superevent):
        # Node name format is group_pipeline or group_pipeline_search
        # If search is provided, we send alerts to both of the relevant nodes
        # NOTE: for test events, group=Test
        event = event_or_superevent
        gp_node = "{group}_{pipeline}".format(group=event.group.name,
            pipeline=event.pipeline.name).lower()
        node_names.append(gp_node)
        if event.search:
            gps_node = gp_node + "_{search}".format(
                search=event.search.name.lower())
            node_names.append(gps_node)
    else:
        error_msg = ('Object is of {0} type; should be an event '
            'or superevent').format(type(event_or_superevent))
        logger.error(error_msg)
        # TODO: way to catch this?
        raise TypeError(error_msg)

    return node_names


def issue_xmpp_alert(event_or_superevent, alert_type="new", file_name="",
    description="", serialized_object=None):
    """
    serialized_object should be a dict
    """

    # Check settings switch for turning off XMPP alerts
    if not settings.SEND_XMPP_ALERTS:
        return

    # Determine LVAlert node names
    node_names = get_xmpp_node_names(event_or_superevent)

    # Get object id
    if is_superevent(event_or_superevent):
        object_id = event_or_superevent.superevent_id
    elif is_event(event_or_superevent):
        object_id = event_or_superevent.graceid()
    else:
        error_msg = ('Object is of {0} type; should be an event '
            'or superevent').format(type(event_or_superevent))
        logger.error(error_msg)
        raise TypeError(error_msg)

    # Create the output dictionary and serialize as JSON.
    lva_data = {
        'file': file_name,
        'uid': object_id,
        'alert_type': alert_type,
        'description': description,
        'labels': [label.name for label in event_or_superevent.labels.all()]
    }
    if serialized_object is not None:
        lva_data['object'] = serialized_object
    # simplejson.dumps is needed to properly handle Decimal fields
    msg = simplejson.dumps(lva_data)

    # Log message for debugging
    logger.debug("issue_xmpp_alert: sending message {msg} for {object_id}" \
        .format(msg=msg, object_id=object_id))

    # Get manager ready for LVAlert Overseer (?)
    if settings.USE_LVALERT_OVERSEER:
        manager = Manager()

    # Loop over LVAlert servers and nodes, issuing the alert to each
    for server in settings.ALERT_XMPP_SERVERS:
        port = settings.LVALERT_OVERSEER_PORTS[server]
        for node_name in node_names:
            
            # Calculate unique message_id and log
            message_id = sha1(node_name + msg).hexdigest()

            # Log message
            logger.info(("issue_xmpp_alert: sending alert type {alert_type} "
                "with message {msg_id} for {obj_id} to {node}").format(
                alert_type=alert_type, msg_id=message_id, obj_id=object_id,
                node=node_name))

            # Try to send with LVAlert Overseer (if enabled)
            success = False
            if settings.USE_LVALERT_OVERSEER:

                # Send with LVAlert Overseer
                success = send_with_lvalert_overseer(node_name, msg, manager,
                    port)

                # If not success, we need to do this the old way.
                if not success:
                    logger.critical(("issue_xmpp_alert: sending message with "
                        "LVAlert Overseer failed, trying lvalert_send"))

            # If not using LVAlert Overseer or if sending with overseer failed,
            # use basic lvalert_send executable (gross)
            if (not settings.USE_LVALERT_OVERSEER) or (not success):
                success, err = send_with_lvalert_send(node_name, msg, server)

                if not success:
                    logger.critical(("issue_xmpp_alert: error sending message "
                        "with lvalert_send: {e}").format(e=err))

