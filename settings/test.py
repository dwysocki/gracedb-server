# Settings for a test GraceDB instance.
# Starts with base.py settings and overrides or adds to them.
from .base import *

CONFIG_NAME = "TEST"

# Debug settings
DEBUG = True
# Don't let django-debug-toolbar edit settings
DEBUG_TOOLBAR_PATCH_SETTINGS = False

# Add cache backend for django-debug-panel
CACHES['debug-panel'] = {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': '/tmp/debug-panel-cache',
    'OPTIONS': {
        'MAX_ENTRIES': 200
    },
}

# Override EMBB email address
# TP (8 Aug 2017): not sure why?
EMBB_MAIL_ADDRESS = 'gracedb@{fqdn}'.format(fqdn=SERVER_FQDN)

# Add middleware classes
MIDDLEWARE_CLASSES += [
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    #'debug_panel.middleware.DebugPanelMiddleware',
    #'middleware.profiling.ProfileMiddleware',
]

# Add to installed apps
add_apps = [
    #'debug_toolbar',
    #'debug_panel',
]
INSTALLED_APPS = tuple(list(INSTALLED_APPS) + add_apps)

# Tuple of IPs which are marked as internal, useful for debugging
# Changed to a list in Django 1.9+
INTERNAL_IPS = (
    '129.89.57.83',
)

