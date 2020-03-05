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
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'gracedb',
        'PASSWORD': DB_PASSWORD,
        'OPTIONS': {
            'init_command': 'SET storage_engine=MyISAM',
        },
    }
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

MIDDLEWARE = [
    'core.middleware.maintenance.MaintenanceModeMiddleware',
    'events.middleware.PerformanceMiddleware',
    'core.middleware.accept.AcceptMiddleware',
    'core.middleware.api.ClientVersionMiddleware',
    'core.middleware.api.CliExceptionMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.proxy.XForwardedForMiddleware',
    'user_sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'ligoauth.middleware.ShibbolethWebAuthMiddleware',
    'ligoauth.middleware.ControlRoomMiddleware',
]

# Set caches:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
        'TIMEOUT': 60,
        'KEY_PREFIX': 'NULL',
    },
    # For API throttles
    'throttles': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'api_throttle_cache', # Table name
    },    
}
 
CACHE_MIDDLEWARE_SECONDS = 5
