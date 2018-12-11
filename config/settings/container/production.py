# Settings for a production GraceDB instance running in a container
from .base import *

DEBUG = False

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True
