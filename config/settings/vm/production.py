# Settings for a production GraceDB instance running on a VM with Puppet
# provisioning. Starts with vm.py settings (which inherits from base.py
# settings) and overrides or adds to them.
from .base import *

TIER = "production"

DEBUG = False

# LVAlert Overseer settings
LVALERT_OVERSEER_INSTANCES = [
    {
        "lvalert_server": "lvalert.cgca.uwm.edu",
        "listen_port": 8000,
    },
]

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True
SEND_MATTERMOST_ALERTS = True

# Safety check on debug mode for production
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for production")
