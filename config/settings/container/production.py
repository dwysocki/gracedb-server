# Settings for a production GraceDB instance running in a container
import copy
from django.core.exceptions import ImproperlyConfigured
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

# If priority server, do some things
if PRIORITY_SERVER:
    # Add custom permissions for API
    default_perms = list(REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])
    default_perms = ['api.permissions.IsPriorityUser'] + default_perms
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = tuple(default_perms)

    # Don't do anything to databases. Priority servers use the master
    # for both read and write operations
else:
    # If not a priority server, we use the read-only replica database
    # for reads and master for writes.

    # Get information from environment variables
    replica_db_name = os.environ.get('DJANGO_REPLICA_DB_NAME', None)
    if replica_db_name is None:
        raise ImproperlyConfigured('Could not get replica database name from '
            'envvars.')
    replica_db_password = os.environ.get('DJANGO_REPLICA_DB_PASSWORD', None)
    if replica_db_password is None:
        raise ImproperlyConfigured('Could not get replica database password '
            'from envvars.')

    # Set up dict and add to DATABASES setting
    read_replica = {
        'NAME': replica_db_name,
        'ENGINE': 'django.db.backends.mysql',
        'USER': os.environ.get('DJANGO_REPLICA_DB_USER', 'gracedb'),
        'PASSWORD': replica_db_password,
        'HOST': os.environ.get('DJANGO_REPLICA_DB_HOST', ''),
        'PORT': os.environ.get('DJANGO_REPLICA_DB_PORT', ''),
        'OPTIONS': {
            'init_command': 'SET storage_engine=MyISAM',
        },
    }
    DATABASES['read_replica'] = read_replica

    # Set up database router
    DATABASE_ROUTERS = ['core.db.routers.NonPriorityRouter',]

# Safety check on debug mode for production
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for production")
