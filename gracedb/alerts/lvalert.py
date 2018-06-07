import os
from multiprocessing import Process
from subprocess import Popen, PIPE
from ligo.overseer.overseer_client import send_to_overseer

import logging
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
