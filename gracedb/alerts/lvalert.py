import logging
from multiprocessing import Process
import os
from subprocess import Popen, PIPE

from ligo.lvalert import LVAlertClient
from ligo.overseer.overseer_client import send_to_overseer

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


def send_with_lvalert_client(node, message, server, username=None,
    password=None, **kwargs):

    # Set up for initializing LVAlertClient instance
    client_settings = {
        'server': server
    }

    # Username and password should be provided for container deployments.
    # For VMs, they won't be, so it will look up the credentials in the
    # .netrc file
    if username is not None:
        client_settings['username'] = username
    if password is not None:
        client_settings['password'] = password

    # Instantiate client
    client = LVAlertClient(**client_settings)

    # Client setup
    client.connect(reattempt=False)
    client.auto_reconnect = False
    client.process(block=False)

    # Send message
    client.publish(node, message)

    # Disconnect
    client.abort()


# OLD
def send_with_lvalert_send(node, message, server):

    # Set up environment for running lvalert_send executable
    env = os.environ.copy()

    # Construct LVAlert command
    cmd = [
        "lvalert_send",
        "--server={server}".format(server=server),
        "--file=-",
        "--node={node}".format(node=node)
    ]

    # Execute command
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
    out, err = p.communicate(message)

    success = True if p.returncode == 0 else False
    return success, err
