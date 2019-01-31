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
