import logging
from multiprocessing import Process
import os


from django.conf import settings
from igwn_alert import client
from igwn_alert_overseer.overseer.overseer_client import overseer_client
from tornado.ioloop import IOLoop
import asyncio
import json


# Set up logger
logger = logging.getLogger(__name__)


def send_with_lvalert_overseer(node_name, message, port):

    # Compile message dictionary
    msg_dict = {
        'node_name': node_name,
        'message': message,
        'action': 'push',
    }

    # Set up client:
    client = overseer_client(host='localhost', port=port)

    # Format message. FIXME maybe move this step into the overseer client?
    msg_dict = json.dumps(msg_dict)

    # Start IOLoop:
    asyncio.set_event_loop(asyncio.new_event_loop())
    resp = client.send_to_overseer(msg_dict, logger)
    IOLoop.instance().start()
    rdict = json.loads(resp.result())

    # Return a boolean indicating whether the message was sent
    # successfully or not
    return True if rdict.get('success', None) is not None else False


def send_with_kafka_client(node, message, server, username=None,
    password=None, group=None, **kwargs):

    # Set up for initializing LVAlertClient instance
    client_settings = {
        'server': server
    }

    # Username and password should be provided for container deployments.
    # For VMs, they won't be, so it will look up the credentials in the
    # hop auth.toml file
    if username is not None:
        client_settings['username'] = username
    if password is not None:
        client_settings['password'] = password
    # if for some reason the group didn't get set correctly, make it the 
    # default
    if group is not None:
        client_settings['group'] = group
    else:
        client_settings['group'] = settings.DEFAULT_IGWN_ALERT_GROUP

    # Instantiate client
    igwn_alert_client = client(**client_settings)

    # Send message
    igwn_alert_client.publish(topic=node, msg=message)

