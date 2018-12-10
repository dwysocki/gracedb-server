# For running a containerized version of the service that gets secrets
# from environment variables. Builds on base.py settings.

import os
from django.core.exceptions import ImproperlyConfigured
from ..base import *

# Get required variables from environment variables ---------------------------
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

# Get Twilio account information from environment
# FIXME
TWILIO_ACCOUNT_SID = os.environ.get('DJANGO_TWILIO_ACCOUNT_SID', 'abcd')
TWILIO_AUTH_TOKEN = os.environ.get('DJANGO_TWILIO_AUTH_TOKEN', 'abcd')

# Database settings -----------------------------------------------------------
DATABASES = {
    'default' : {
        'NAME': db_name,
        'ENGINE': 'django.db.backends.mysql',
        'USER': os.environ.get('DJANGO_DB_USER', 'gracedb'),
        'PASSWORD': db_password,
        'HOST': os.environ.get('DJANGO_DB_HOST', ''),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        'OPTIONS': {
            'init_command': 'SET storage_engine=MyISAM',
        },
    }
}

# Main server "hostname" - a little hacky but OK
SERVER_HOSTNAME = SERVER_FQDN.split('.')[0]

# Update allowed hosts from environment variables -----------------------------
hosts_from_env = os.environ.get('DJANGO_ALLOWED_HOSTS', None)
if hosts_from_env is not None:
    ALLOWED_HOSTS += hosts_from_env.split(',')
ALLOWED_HOSTS += [SERVER_FQDN]

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
