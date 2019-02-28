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

# Get Twilio account information from environment
TWILIO_ACCOUNT_SID = os.environ.get('DJANGO_TWILIO_ACCOUNT_SID', None)
if TWILIO_ACCOUNT_SID is None:
    raise ImproperlyConfigured('Could not get Twilio acct SID from envvars.')

TWILIO_AUTH_TOKEN = os.environ.get('DJANGO_TWILIO_AUTH_TOKEN', None)
if TWILIO_AUTH_TOKEN is None:
    raise ImproperlyConfigured('Could not get Twilio auth token from envvars.')

# Get email settings from environment
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST = os.environ.get('SMTP_HOST', 'localhost')
EMAIL_HOST_USER = os.environ.get('SMTP_USERNAME', '')
EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
ALERT_EMAIL_FROM = os.environ.get('DJANGO_ALERT_EMAIL_FROM', None)
if ALERT_EMAIL_FROM is None:
    raise ImproperlyConfigured(
        "Could not get 'alert from email' from envvars.")

# Database settings -----------------------------------------------------------
DATABASES = {
    'default' : {
        'NAME': db_name,
        'ENGINE': 'django.db.backends.mysql',
        'USER': db_user,
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

# LVAlert Overseer settings - get from environment
LVALERT_OVERSEER_INSTANCES = [
    {
        "lvalert_server": lvalert_server,
        "listen_port": int(lvalert_overseer_port),
        "username": lvalert_user,
        "password": lvalert_password,
    },
]

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
