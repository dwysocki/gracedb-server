# Settings for a production GraceDB instance running in a container
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

# If priority server, only allow priority users
if PRIORITY_SERVER:
    # Add custom permissions for API
    default_perms = list(REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])
    default_perms = ['api.permissions.IsPriorityUser'] + default_perms
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = tuple(default_perms)


# TP, March 2019: for now, it looks infeasible to use multiple databases
# since there are many operations which normal LVC users can do that
# do a write and then a read very soon after.  And we can't rely on
# the read replica being updated quickly enough for that to work.
# So there are several workflows that need to be redone in order for
# this to be possible, but it's not obvious that they even can be
# reworked properly.  I.e. this is a much bigger project than expected
# so we're going to have to revisit it at some point.  We'll leave the
# config here for now.
#    # If not a priority server, we use the read-only replica database
#    # for reads and master for writes.
#    # The username, password, and database name are all replicated
#    # from the production database
#
#    # Set up dict and add to DATABASES setting
#    read_replica = {
#        'NAME': DATABASES['default']['NAME'],
#        'ENGINE': 'django.db.backends.mysql',
#        'USER': DATABASES['default']['USER'],
#        'PASSWORD': DATABASES['default']['PASSWORD'],
#        'HOST': os.environ.get('DJANGO_REPLICA_DB_HOST', ''),
#        'PORT': os.environ.get('DJANGO_REPLICA_DB_PORT', ''),
#        'OPTIONS': {
#            'init_command': 'SET storage_engine=MyISAM',
#        },
#    }
#    DATABASES['read_replica'] = read_replica
#
#    # Set up database router
#    DATABASE_ROUTERS = ['core.db.routers.NonPriorityRouter',]

# Safety check on debug mode for production
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for production")
