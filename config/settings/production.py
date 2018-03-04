# Settings for a production GraceDB instance.
# Starts with base.py settings and overrides or adds to them.
from .base import *

# TP 12/22/2016: I don't think we need this anymore.
#SHIB_AUTHENTICATION_SESSION_INITIATOR = 'https://archie.phys.uwm.edu/Shibboleth.sso/Login'

CONFIG_NAME = "PRODUCTION"

# TP 12/22/2016: Doesn't seem to be used anywhere.
SITE_ID = 3

# LVAlert Overseer settings
ALERT_XMPP_SERVERS = ["lvalert.cgca.uwm.edu"]
LVALERT_OVERSEER_PORTS = {
    "lvalert.cgca.uwm.edu": 8000,
}

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True
