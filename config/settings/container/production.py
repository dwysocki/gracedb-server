# Settings for a production GraceDB instance running in a container
from .base import *

DEBUG = False

# Turn on alerts
SEND_XMPP_ALERTS = True
SEND_PHONE_ALERTS = True
SEND_EMAIL_ALERTS = True

# TP, March 2019: for now, it looks infeasible to use multiple databases
# since there are many operations which normal LVC users can do that
# do a write and then a read very soon after.  And we can't rely on
# the read replica being updated quickly enough for that to work.
# So there are several workflows that need to be redone in order for
# this to be possible, but it's not obvious that they even can be
# reworked properly.  I.e. this is a much bigger project than expected
# so we're going to have to revisit it at some point.  We'll leave the
# config here for now.
# if not PRIORITY_SERVER:
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

# Set up Sentry for error logging
sentry_dsn = get_from_env('DJANGO_SENTRY_DSN', fail_if_not_found=False)
if sentry_dsn is not None:
    USE_SENTRY = True

    # Set up Sentry
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        environment='production',
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()]
    )

    # Turn off default admin error emails
    LOGGING['loggers']['django.request']['handlers'] = []

# Safety check on debug mode for production
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for production")
