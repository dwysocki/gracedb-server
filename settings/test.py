# Settings for a test GraceDB instance.
# Starts with base.py settings and overrides or adds to them.
from .base import *

CONFIG_NAME = "TEST"

# Debug settings
DEBUG = True
# Don't let django-debug-toolbar edit settings
DEBUG_TOOLBAR_PATCH_SETTINGS = False

# Override EMBB email address
# TP (8 Aug 2017): not sure why?
EMBB_MAIL_ADDRESS = 'gracedb@{fqdn}'.format(fqdn=SERVER_FQDN)

# Add middleware
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    #'middleware.profiling.ProfileMiddleware',
]

# Add to installed apps
INSTALLED_APPS += [
    'debug_toolbar',
]

# Tuple of IPs which are marked as internal, useful for debugging
# Changed to a list in Django 1.9+
INTERNAL_IPS = [
    #'129.89.57.164',
]

