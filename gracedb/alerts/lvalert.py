import logging
import os
import asyncio
import datetime
import json
import time
import functools

from django.conf import settings
from igwn_alert import client
from igwn_alert_overseer.overseer.overseer_client import overseer_client
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from asyncio.exceptions import InvalidStateError

# Set up logger
logger = logging.getLogger(__name__)

# man, just shorten the variable name
OVERSEER_TIMEOUT = settings.OVERSEER_TIMEOUT

def timeout_and_stop(io_loop):
    logger.critical(f'Overseer IO Loop timed out after {OVERSEER_TIMEOUT} seconds.')
    io_loop.stop()


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

    alert_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(alert_loop)
        
        # Start the async request to push the message to the overseer, and 
        # await the success/failure response.
        resp = client.send_to_overseer(msg_dict, logger)

        # Start the async I/O loop within the current thread
        io_loop = IOLoop.instance()

        # Construct a callable that passes io_loop as an argument
        overseer_timeout = functools.partial(timeout_and_stop, io_loop)

        # Add a timeout for the scenario where the overseer server isn't 
        # running or responding. This shouldn't actually happen, but hey.
        io_loop.add_timeout(time.time() + OVERSEER_TIMEOUT, overseer_timeout)

        # Start the I/O loop
        io_loop.start()

        # Interpret the response
        rdict = json.loads(resp.result())

    # Two scenarios here: the overseer client code gives a StreamClosedError
    # when the I/O loop was stopped after it timed out. I think the 
    # InvalidStateError came as a result of prior implementation of this logic, 
    # so i don't think it would occur again... but if it does it still represents
    # an invalid response from the overseer, so the alert should be sent again.
    except (StreamClosedError, InvalidStateError) as e:
        # close the loop and free up the port:
        alert_loop.close()
        
        # return false and then attempt to send with the client code.
        return False
    finally:
        # close the loop and free up the port:
        alert_loop.close()

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

