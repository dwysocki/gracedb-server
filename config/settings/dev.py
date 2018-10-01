# Settings for a test GraceDB instance.
# Starts with base.py settings and overrides or adds to them.
from .base import *
import socket

CONFIG_NAME = "TEST"

# Debug settings
DEBUG = True

# Override EMBB email address
# TP (8 Aug 2017): not sure why?
EMBB_MAIL_ADDRESS = 'gracedb@{fqdn}'.format(fqdn=SERVER_FQDN)

# Add middleware
debug_middleware = 'debug_toolbar.middleware.DebugToolbarMiddleware'
MIDDLEWARE += [
    debug_middleware,
    #'silk.middleware.SilkyMiddleware',
    #'core.middleware.profiling.ProfileMiddleware',
]

# Add to installed apps
INSTALLED_APPS += [
    'debug_toolbar',
    #'silk'
]

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Settings for django-silk profiler
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
if 'silk' in INSTALLED_APPS:
    # Needed to prevent RequestDataTooBig for files > 2.5 MB
    # when silk is being used. This setting is typically used to
    # prevent DOS attacks, so should not be changed in production.
    DATA_UPLOAD_MAX_MEMORY_SIZE = 20*(1024**2)

# Add XForwardedFor middleware directly before debug_toolbar middleware
# if debug_toolbar is enabled and DEBUG is True.
if DEBUG and debug_middleware in MIDDLEWARE:
    MIDDLEWARE.insert(MIDDLEWARE.index(debug_middleware),
        'core.middleware.proxy.XForwardedForMiddleware')

# Tuple of IPs which are marked as internal, useful for debugging.
# Tanner (5 Dec. 2017): DON'T CHANGE THIS! Django Debug Toolbar exposes
# some headers which we want to keep hidden.  So to be safe, we only allow
# it to be used through this server.  You need to configure a SOCKS proxy
# on your local machine to use DJDT (see admin docs).
INTERNAL_IPS = [
    socket.gethostbyname(socket.gethostname()),
]
