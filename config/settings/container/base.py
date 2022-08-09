# For running a containerized version of the service that gets secrets
# from environment variables. Builds on base.py settings.
import os
from django.core.exceptions import ImproperlyConfigured
from ..base import *

# Get required variables from environment variables ---------------------------
# Get database user from environment and check
db_user = os.environ.get('DJANGO_DB_USER', None)
if db_user is None:
    raise ImproperlyConfigured('Could not get database user from envvars.')

# Get database password from environment and check
db_password = os.environ.get('DJANGO_DB_PASSWORD', None)
if db_password is None:
    raise ImproperlyConfigured('Could not get database password from envvars.')

# Get database name from environment and check
db_name = os.environ.get('DJANGO_DB_NAME', None)
if db_name is None:
    raise ImproperlyConfigured('Could not get database name from envvars.')

# Secret key for a Django installation
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', None)
if SECRET_KEY is None:
    raise ImproperlyConfigured('Could not get secret key from envvars.')

# Get primary FQDN
SERVER_FQDN = os.environ.get('DJANGO_PRIMARY_FQDN', None)
if SERVER_FQDN is None:
    raise ImproperlyConfigured('Could not get FQDN from envvars.')
LIGO_FQDN = SERVER_FQDN

# Turn LVAlert on/off from the environment. Adding this
# to turn lvalerts on/off from docker compose/update instead
# of having to rebuild containers. If the environment variable
# isn't set, then revert to the hardwired behavior:
xmpp_env_var = get_from_env('SEND_LVALERT_XMPP_ALERTS',
                   default_value=SEND_XMPP_ALERTS,
                   fail_if_not_found=False)
# Fix for other boolean values:
if (isinstance(xmpp_env_var, str) and
    xmpp_env_var.lower() in ['true','t','1']):
    SEND_XMPP_ALERTS=True
elif (isinstance(xmpp_env_var, str) and
    xmpp_env_var.lower() in ['false','f','0']):
    SEND_XMPP_ALERTS=False
else:
    SEND_XMPP_ALERTS = True


# Get lvalert_overseer status:
lvalert_on  = get_from_env(
    'ENABLE_LVALERT_OVERSEER',
    default_value=False,
    fail_if_not_found=False
)
if (isinstance(lvalert_on, str) and
    lvalert_on.lower() in ['true', 't', '1']):
        lvalert_overseer_on  = True
else:
    lvalert_overseer_on  = False

# Get igwn_alert_overseer status:
igwn_alert_on  = get_from_env(
    'ENABLE_IGWN_OVERSEER',
    default_value=False,
    fail_if_not_found=False
)
if (isinstance(igwn_alert_on, str) and
    igwn_alert_on.lower() in ['true', 't', '1']):
        igwn_alert_overseer_on  = True
else:
    igwn_alert_overseer_on  = False

# Get LVAlert server
lvalert_server = os.environ.get('LVALERT_SERVER', None)
if lvalert_server is None:
    raise ImproperlyConfigured('Could not get LVAlert server from envvars.')

# Get LVAlert Overseer listen port
lvalert_overseer_port = os.environ.get('LVALERT_OVERSEER_PORT', None)
if lvalert_overseer_port is None:
    raise ImproperlyConfigured('Could not get LVAlert overseer port '
        'from envvars.')

# Get LVAlert username
lvalert_user = os.environ.get('LVALERT_USER', None)
if lvalert_user is None:
    raise ImproperlyConfigured('Could not get LVAlert username from envvars.')

# Get LVAlert password
lvalert_password = os.environ.get('LVALERT_PASSWORD', None)
if lvalert_password is None:
    raise ImproperlyConfigured('Could not get LVAlert password from envvars.')

# Get igwn-alert server
igwn_alert_server = os.environ.get('IGWN_ALERT_SERVER', None)
if lvalert_server is None:
    raise ImproperlyConfigured('Could not get igwn-alert server from envvars.')

# Get igwn-alert Overseer listen port
igwn_alert_overseer_port = os.environ.get('IGWN_ALERT_OVERSEER_PORT', None)
if lvalert_overseer_port is None:
    raise ImproperlyConfigured('Could not get igwn-alert overseer port '
        'from envvars.')

# Get igwn-alert username
igwn_alert_user = os.environ.get('IGWN_ALERT_USER', None)
if lvalert_user is None:
    raise ImproperlyConfigured('Could not get igwn-alert username from envvars.')

# Get igwn-alert password
igwn_alert_password = os.environ.get('IGWN_ALERT_PASSWORD', None)
if lvalert_password is None:
    raise ImproperlyConfigured('Could not get igwn-alert password from envvars.')

# Get Twilio account information from environment
TWILIO_ACCOUNT_SID = os.environ.get('DJANGO_TWILIO_ACCOUNT_SID', None)
if TWILIO_ACCOUNT_SID is None:
    raise ImproperlyConfigured('Could not get Twilio acct SID from envvars.')

TWILIO_AUTH_TOKEN = os.environ.get('DJANGO_TWILIO_AUTH_TOKEN', None)
if TWILIO_AUTH_TOKEN is None:
    raise ImproperlyConfigured('Could not get Twilio auth token from envvars.')

# Get maintenance mode settings from environment
maintenance_mode = get_from_env(
    'DJANGO_MAINTENANCE_MODE_ACTIVE',
    default_value=False,
    fail_if_not_found=False
)

# DB "cool-down" factor for when a db conflict is detected. This
# factor scales a random number of seconds between zero and one.
DB_SLEEP_FACTOR = get_from_env(
        'DJANGO_DB_SLEEP_FACTOR',
        default_value=1.0,
        fail_if_not_found=False
)
# Fix the factor (str to float)
try:
    DB_SLEEP_FACTOR = float(DB_SLEEP_FACTOR)
except:
    DB_SLEEP_FACTOR = 1.0

if (isinstance(maintenance_mode, str) and
    maintenance_mode.lower() in ['true', 't', '1']):
    MAINTENANCE_MODE = True
MAINTENANCE_MODE_MESSAGE = \
    get_from_env('DJANGO_MAINTENANCE_MODE_MESSAGE', fail_if_not_found=False)

# Get info banner settings from environment
info_banner_enabled = get_from_env(
    'DJANGO_INFO_BANNER_ENABLED',
    default_value=False,
    fail_if_not_found=False
)
# fix for other booleans:
if (isinstance(info_banner_enabled, str) and
    info_banner_enabled.lower() in ['true','t','1']):
    INFO_BANNER_ENABLED = True
INFO_BANNER_MESSAGE = \
    get_from_env('DJANGO_INFO_BANNER_MESSAGE', fail_if_not_found=False)

# Get email settings from environment
EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_SES_ACCESS_KEY_ID = get_from_env('AWS_SES_ACCESS_KEY_ID')
AWS_SES_SECRET_ACCESS_KEY = get_from_env('AWS_SES_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = get_from_env('AWS_SES_REGION_NAME',
    default_value='us-west-2', fail_if_not_found=False)
AWS_SES_REGION_ENDPOINT = get_from_env('AWS_SES_REGION_ENDPOINT',
    default_value='email.us-west-2.amazonaws.com', fail_if_not_found=False)
AWS_SES_AUTO_THROTTLE = 0.25
ALERT_EMAIL_FROM = get_from_env('DJANGO_ALERT_EMAIL_FROM')

# AWS Elasticache settings:
AWS_ELASTICACHE_ADDR = get_from_env('DJANGO_AWS_ELASTICACHE_ADDR')
#CACHES['default'] = {
#        'BACKEND': 'django_elasticache.memcached.ElastiCache',
#        'LOCATION': AWS_ELASTICACHE_ADDR,
#        'OPTIONS': {
#            'IGNORE_CLUSTER_ERRORS': True,
#        },
#    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': AWS_ELASTICACHE_ADDR,
    },
    # For API throttles
    'throttles': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'api_throttle_cache', # Table name
    },
}

MIDDLEWARE = [
    'core.middleware.maintenance.MaintenanceModeMiddleware',
    'events.middleware.PerformanceMiddleware',
    'core.middleware.accept.AcceptMiddleware',
    'core.middleware.api.ClientVersionMiddleware',
    'core.middleware.api.CliExceptionMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'core.middleware.proxy.XForwardedForMiddleware',
    'user_sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'ligoauth.middleware.ShibbolethWebAuthMiddleware',
    'ligoauth.middleware.ControlRoomMiddleware',
]




# Priority server settings ----------------------------------------------------
PRIORITY_SERVER = False
is_priority_server = get_from_env('DJANGO_PRIORITY_SERVER', None,
    fail_if_not_found=False)
if (isinstance(is_priority_server, str) and
    is_priority_server.lower() in ['true', 't']):
    PRIORITY_SERVER = True

# If priority server, only allow priority users to the API
if PRIORITY_SERVER:
    # Add custom permissions for the API
    default_perms = list(REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])
    default_perms = ['api.permissions.IsPriorityUser'] + default_perms
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = tuple(default_perms)


# Database settings -----------------------------------------------------------

# New postgresql database
# Configured for the CI pipeline:
# https://docs.gitlab.com/ee/ci/services/postgres.html
DATABASES = {
    'default' : {
        'NAME': db_name,
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': os.environ.get('DJANGO_DB_HOST', ''),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        'CONN_MAX_AGE': 3600,
        'TEST' : {
            'NAME': 'gracedb_test_db',
        },
    },
}


# Adding a fun conditional to control Amazon AWS Elasticache settings.
# Here's the logic: 
#  1) check for the existence of the DJANGO_AWS_ELASTICACHE_ADDR address
#     variable. If it's present, then load the CACHE settings and MIDDLEWARE
#     settings required for AWS elasticache'ing
#
#  2) Check for the existence of DJANGO_AWS_ELASTICACHE_TIMEOUT variable. This
#     will control the cache timeout. If it's not set, default to 30s.
#
#  3) If not, default to old cache settings, which is effectively no-caches. 

try:
    AWS_ELASTICACHE_ADDR = get_from_env('DJANGO_AWS_ELASTICACHE_ADDR')

    # I *think* if the variable isn't set, then that should raise an exception 
    # and then it should skip the rest:

    try:
        # This has to be an int, but it gets it from then env as a string.
        AWS_ELASTICACHE_TIMEOUT = int(get_from_env('DJANGO_AWS_ELASTICACHE_TIMEOUT'))
    except:
        AWS_ELASTICACHE_TIMEOUT = 30

    # Set the middleware timeout equal to the cache timeout:
    CACHE_MIDDLEWARE_SECONDS = AWS_ELASTICACHE_TIMEOUT

    # Load modified caching middleware:
    # https://docs.djangoproject.com/en/2.2/ref/middleware/#middleware-ordering
    MIDDLEWARE = [
        'django.middleware.cache.UpdateCacheMiddleware',
        'django.middleware.gzip.GZipMiddleware',
        'events.middleware.PerformanceMiddleware',
        'core.middleware.accept.AcceptMiddleware',
        'core.middleware.api.ClientVersionMiddleware',
        'core.middleware.api.CliExceptionMiddleware',
        'core.middleware.proxy.XForwardedForMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'user_sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'core.middleware.maintenance.MaintenanceModeMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.cache.FetchFromCacheMiddleware',
        'ligoauth.middleware.ShibbolethWebAuthMiddleware',
        'ligoauth.middleware.ControlRoomMiddleware',
    ]

    # Set caches:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': AWS_ELASTICACHE_ADDR,
            'TIMEOUT': AWS_ELASTICACHE_TIMEOUT,
            'KEY_PREFIX': 'NULL',
        },
        # For API throttles
        'throttles': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'api_throttle_cache', # Table name
        },    
    }
except:
    pass

# Main server "hostname" - a little hacky but OK
SERVER_HOSTNAME = SERVER_FQDN.split('.')[0]

# LVAlert Overseer settings - get from environment
LVALERT_OVERSEER_INSTANCES = []
LVALERT_OVERSEER_INSTANCES = [
    {
        "lvalert_server": lvalert_server,
        "listen_port": int(lvalert_overseer_port),
        "username": lvalert_user,
        "password": lvalert_password,
    }]

if igwn_alert_overseer_on:
    LVALERT_OVERSEER_INSTANCES.append(
    {
        "lvalert_server": igwn_alert_server,
        "listen_port": int(igwn_alert_overseer_port),
        "username": igwn_alert_user,
        "password": igwn_alert_password,
    }
    )

INSTANCE_STUB = """
<li>Phone alerts (calls/SMS) are {0}</li>
<li>Email alerts are {1}</li>
<li><span class="text-monospace">LVAlert</span> messages to <span class="text-monospace">{2}</span> are {3}</li>
"""

INSTANCE_LIST = INSTANCE_STUB.format(ENABLED[SEND_PHONE_ALERTS],
                                ENABLED[SEND_EMAIL_ALERTS],
                                LVALERT_OVERSEER_INSTANCES[0]['lvalert_server'],
                                ENABLED[SEND_XMPP_ALERTS])

if (len(LVALERT_OVERSEER_INSTANCES) == 2):
    IGWN_STUB = '<li><span class="text-monospace">igwn-alert</span> messages to <span class="text-monospace">{0}</span> are {1}</li>'
    IGWN_LIST = IGWN_STUB.format(LVALERT_OVERSEER_INSTANCES[1]['lvalert_server'],
                                ENABLED[SEND_XMPP_ALERTS])
    INSTANCE_LIST = INSTANCE_LIST + IGWN_LIST

# Use full client certificate to authenticate
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    'api.backends.GraceDbAuthenticatedAuthentication',
    'api.backends.GraceDbX509FullCertAuthentication',
    'api.backends.GraceDbBasicAuthentication',
)

# Update allowed hosts from environment variables -----------------------------
hosts_from_env = os.environ.get('DJANGO_ALLOWED_HOSTS', None)
if hosts_from_env is not None:
    ALLOWED_HOSTS += hosts_from_env.split(',')
ALLOWED_HOSTS += [SERVER_FQDN]

# Email settings - dependent on server hostname and FQDN ----------------------
SERVER_EMAIL = ALERT_EMAIL_FROM
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = ALERT_EMAIL_FROM
ALERT_TEST_EMAIL_TO = []
# EMBB email settings
EMBB_MAIL_ADDRESS = 'embb@{fqdn}.ligo.org'.format(fqdn=SERVER_FQDN)
EMBB_SMTP_SERVER = 'localhost'
EMBB_MAIL_ADMINS = [admin[1] for admin in ADMINS]
EMBB_IGNORE_ADDRESSES = ['Mailer-Daemon@{fqdn}'.format(fqdn=SERVER_FQDN)]

# Set up logging to stdout only
for key in LOGGING['loggers']:
    LOGGING['loggers'][key]['handlers'] = ['console']
LOGGING['loggers']['django.request']['handlers'].append('mail_admins')

# Turn off debug/error emails when in maintenance mode.
if MAINTENANCE_MODE:
    LOGGING['loggers']['django.request']['handlers'].remove('mail_admins')
