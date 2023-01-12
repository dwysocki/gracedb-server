# For running a VM that is provisioned by Puppet with a secret.py file
# for secret settings
from ..base import *
# Get secret settings:
# DB_PASSWORD, SECRET_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from ..secret import *
import socket

# Nested dict of settings for all databases
DATABASES = {
    'default' : {
        'NAME': 'gracedb',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'gracedb',
        'PASSWORD': DB_PASSWORD,
        'HOST':'127.0.0.1',
        'PORT':'5432',
        'CONN_MAX_AGE': 3600,
    },
}

# Set up allowed hosts
SERVER_FQDN = socket.getfqdn()
SERVER_HOSTNAME = INTERNAL_HOSTNAME
LIGO_FQDN = '{hostname}.ligo.org'.format(hostname=SERVER_HOSTNAME)
ALLOWED_HOSTS += [SERVER_FQDN, LIGO_FQDN]

# Email settings - dependent on server hostname and FQDN ----------------------
EMAIL_HOST = 'localhost'
SERVER_EMAIL = 'GraceDB <gracedb@{fqdn}>'.format(fqdn=SERVER_FQDN)
ALERT_EMAIL_FROM = SERVER_EMAIL
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = SERVER_EMAIL
ALERT_TEST_EMAIL_TO = []
# EMBB email settings
EMBB_MAIL_ADDRESS = 'embb@{fqdn}.ligo.org'.format(fqdn=SERVER_FQDN)
EMBB_SMTP_SERVER = 'localhost'
EMBB_MAIL_ADMINS = [admin[1] for admin in ADMINS]
EMBB_IGNORE_ADDRESSES = ['Mailer-Daemon@{fqdn}'.format(fqdn=SERVER_FQDN)]

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
    'ligoauth.middleware.ShibbolethWebAuthMiddleware',
    'ligoauth.middleware.ControlRoomMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

# Set caches:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'localhost:11211',
        'TIMEOUT': 60,
        'KEY_PREFIX': 'NULL',
        'OPTIONS': {
            'ignore_exc': True,
            }
    },
    # For API throttles
    'throttles': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'api_throttle_cache', # Table name
    },    
}
 
CACHE_MIDDLEWARE_SECONDS = 5

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

BETA_REPORTS_LINK = True

INSTANCE_STUB = """
<li>Phone alerts (calls/SMS) are {0}</li>
<li>Email alerts are {1}</li>
<li><span class="text-monospace">igwn-alert</span> messages to <span class="text-monospace">{2}</span> are {3}</li>
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

# Set SciToken accepted audience to server FQDN
SCITOKEN_AUDIENCE = ["https://" + SERVER_FQDN, "https://" + LIGO_FQDN]
