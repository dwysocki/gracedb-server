from __future__ import absolute_import
import logging
import os
import simplejson
import socket
import sys

from django.core.mail import EmailMessage
from django.conf import settings

from core.time_utils import gpsToUtc
from events.permission_utils import is_external
from events.query import filter_for_labels
from events.shortcuts import is_event
from superevents.shortcuts import is_superevent
from .lvalert import send_with_lvalert_overseer, send_with_lvalert_send

# Set up logger
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
        superevent = event_or_superevent
        if superevent.is_production():
            superevent_node = 'superevent'
        elif superevent.is_mdc():
            superevent_node = 'mdc_superevent'
        else:
            superevent_node = 'test_superevent'
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


def issue_xmpp_alerts(event_or_superevent, alert_type, serialized_object,
    serialized_parent=None):
    """
    serialized_object should be a dict
    """

    # Check settings switch for turning off XMPP alerts
    if not settings.SEND_XMPP_ALERTS:
        return

    # Determine LVAlert node names
    node_names = get_xmpp_node_names(event_or_superevent)

    # Get uid
    uid = event_or_superevent.graceid

    # Create the output dictionary and serialize as JSON.
    lva_data = {
        'uid': uid,
        'alert_type': alert_type,
        'data': serialized_object,
    }
    # Add serialized "parent" object
    if serialized_parent is not None:
        lva_data['object'] = serialized_parent

    # Dump to JSON format:
    # simplejson.dumps is needed to properly handle Decimal fields
    msg = simplejson.dumps(lva_data)

    # Log message for debugging
    logger.info("issue_xmpp_alerts: sending message {msg} for {uid}" \
        .format(msg=msg, uid=uid))

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
            logger.info(("issue_xmpp_alerts: sending alert type {alert_type} "
                "with message {msg_id} for {uid} to {node}").format(
                alert_type=alert_type, msg_id=message_id, uid=uid,
                node=node_name))

            # Try to send with LVAlert Overseer (if enabled)
            success = False
            if settings.USE_LVALERT_OVERSEER:

                # Send with LVAlert Overseer
                success = send_with_lvalert_overseer(node_name, msg, manager,
                    port)

                # If not success, we need to do this the old way.
                if not success:
                    logger.critical(("issue_xmpp_alerts: sending message with "
                        "LVAlert Overseer failed, trying lvalert_send"))

            # If not using LVAlert Overseer or if sending with overseer failed,
            # use basic lvalert_send executable (gross)
            if (not settings.USE_LVALERT_OVERSEER) or (not success):
                success, err = send_with_lvalert_send(node_name, msg, server)

                if not success:
                    logger.critical(("issue_xmpp_alerts: error sending "
                        "message with lvalert_send: {e}").format(e=err))

