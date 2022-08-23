import logging
from multiprocessing import Process
import os
from subprocess import Popen, PIPE

from django.conf import settings
from igwn_alert import client
from igwn_alert_overseer.overseer.overseer_client import send_to_overseer

# Set up logger
logger = logging.getLogger(__name__)


def send_with_lvalert_overseer(node_name, message, manager, port):

    # Get rdict from manager (?)
    rdict = manager.dict()

    # Compile message dictionary
    msg_dict = {
        'node_name': node_name,
        'message': message,
        'action': 'push',
    }

    # Send to overseer (?)
    p = Process(target=send_to_overseer, args=(msg_dict, rdict,
        logger, True, port))
    p.start()
    p.join()

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

