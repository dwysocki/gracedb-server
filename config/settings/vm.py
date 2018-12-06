# For running a VM that is provisioned by Puppet with
# a secret.py file for secret settings

# Get secret settings:
# DEFAULT_DB_PASSWORD, DEFAULT_SECRET_KEY, TWILIO_ACCOUNT_SID,
# TWILIO_AUTH_TOKEN
from .base import *
from .secret import *

# Nested dict of settings for all databases
DATABASES = {
    'default' : {
        'NAME': 'gracedb',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'gracedb',
        'PASSWORD': DEFAULT_DB_PASSWORD,
        'OPTIONS': {
            'init_command': 'SET storage_engine=MyISAM',
        },
    }
}

# Secret key for a Django installation
SECRET_KEY = DEFAULT_SECRET_KEY
