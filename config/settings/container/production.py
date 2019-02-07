# Settings for a production GraceDB instance running in a container
from .base import *

DEBUG = False

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True

# Priority server?
PRIORITY_SERVER = False
is_priority_server = os.environ.get('DJANGO_PRIORITY_SERVER', None)
if (isinstance(is_priority_server, str) and
    is_priority_server.lower() in ['true', 't']):
    PRIORITY_SERVER = True

# If priority server, add custom permissions for API
if PRIORITY_SERVER:
    default_perms = list(REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])
    default_perms = ['api.permissions.IsPriorityUser'] + default_perms
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = tuple(default_perms)

# Safety check on debug mode for production
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for production")
