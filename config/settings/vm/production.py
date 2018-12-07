# Settings for a production GraceDB instance running on a VM with Puppet
# provisioning. Starts with vm.py settings (which inherits from base.py
# settings) and overrides or adds to them.
from .base import *

# LVAlert Overseer settings
ALERT_XMPP_SERVERS = ["lvalert.cgca.uwm.edu"]
LVALERT_OVERSEER_PORTS = {
    "lvalert.cgca.uwm.edu": 8000,
}

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True
