# For running a containerized version of the service that gets secrets
# from environment variables. Builds on base.py settings.

import os
from django.core.exceptions import ImproperlyConfigured
from .base import *

# Get database password from environment and check
DB_PASSWORD = os.environ.get('DJANGO_DB_PASSWORD', None)
if DB_PASSWORD is None:
    raise ImproperlyConfigured('Could not get database password from envvars.')

# Secret key for a Django installation
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', None)
if SECRET_KEY is None:
    raise ImproperlyConfigured('Could not get secret key from envvars.')

# Get Twilio account information from environment
# FIXME
TWILIO_ACCOUNT_SID = os.environ.get('DJANGO_TWILIO_ACCOUNT_SID', 'abcd')
TWILIO_AUTH_TOKEN = os.environ.get('DJANGO_TWILIO_AUTH_TOKEN', 'abcd')

# Database settings
DATABASES = {
    'default' : {
        'NAME': 'gracedb',
        'ENGINE': 'django.db.backends.mysql',
        'USER': os.environ.get('DJANGO_DB_USER', 'gracedb'),
        'PASSWORD': DB_PASSWORD,
        'HOST': os.environ.get('DJANGO_DB_HOST', ''),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        'OPTIONS': {
            'init_command': 'SET storage_engine=MyISAM',
        },
    }
}


