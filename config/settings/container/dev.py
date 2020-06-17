# Settings for a test/dev GraceDB instance running in a container
from .base import *

CONFIG_NAME = "DEV"

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
    #'core.middleware.admin.AdminsOnlyMiddleware',
]

# Add to installed apps
INSTALLED_APPS += [
    'debug_toolbar',
    #'silk'
]

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Turn on XMPP alerts
SEND_XMPP_ALERTS = True

# Enforce that phone and email alerts are off
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False


# Settings for django-silk profiler
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
if 'silk' in INSTALLED_APPS:
    # Needed to prevent RequestDataTooBig for files > 2.5 MB
    # when silk is being used. This setting is typically used to
    # prevent DOS attacks, so should not be changed in production.
    DATA_UPLOAD_MAX_MEMORY_SIZE = 20*(1024**2)

# Tuple of IPs which are marked as internal, useful for debugging.
# Tanner (5 Dec. 2017): DON'T CHANGE THIS! Django Debug Toolbar exposes
# some headers which we want to keep hidden.  So to be safe, we only allow
# it to be used through this server.  You need to configure a SOCKS proxy
# on your local machine to use DJDT (see admin docs).
INTERNAL_IPS = [
    INTERNAL_IP_ADDRESS,
]

# Set up Sentry for error logging
sentry_dsn = get_from_env('DJANGO_SENTRY_DSN', fail_if_not_found=False)
if sentry_dsn is not None:
    USE_SENTRY = True

    # Set up Sentry
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        environment='test',
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()]
    )

    # Turn off default admin error emails
    LOGGING['loggers']['django.request']['handlers'] = []

# Home page stuff
INSTANCE_TITLE = 'GraceDB Development Server'
INSTANCE_INFO = """
<h5>Development Instance</h5>
<hr>
<p>
This GraceDB instance is designed for GraceDB maintainers to develop and
test in the AWS cloud architecture. There is <b>no guarantee</b> that the
behavior of this instance will mimic the production system at any time. 
Events and associated data may change or be removed at any time. 
</p>
<ul>
<li>Phone and e-mail alerts are turned off.</li>
<li>Only LIGO logins are provided (no login via InCommon or Google).</li>
<li>LVAlert messages are sent to lvalert-dev.cgca.uwm.edu.</li>
</ul>
"""

if AWS_ELASTICACHE_ADDR:
    CACHES['default']['KEY_PREFIX'] = '1'
    CACHE_MIDDLEWARE_KEY_PREFIX = '1'
