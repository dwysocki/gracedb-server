# Settings for a production GraceDB instance running in a container
from .base import *

DEBUG = False

# LVAlert Overseer settings
ALERT_XMPP_SERVERS = ["lvalert.cgca.uwm.edu"]
LVALERT_OVERSEER_PORTS = {
    "lvalert.cgca.uwm.edu": 8000,
}

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True
