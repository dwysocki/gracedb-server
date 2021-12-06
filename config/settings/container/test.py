# Settings for a test/dev GraceDB instance running in a container
from .base import *

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
    #'core.middleware.admin.AdminsOnlyMiddleware',
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

# Tuple of IPs which are marked as internal, useful for debugging.
# Tanner (5 Dec. 2017): DON'T CHANGE THIS! Django Debug Toolbar exposes
# some headers which we want to keep hidden.  So to be safe, we only allow
# it to be used through this server.  You need to configure a SOCKS proxy
# on your local machine to use DJDT (see admin docs).
INTERNAL_IPS = [
    INTERNAL_IP_ADDRESS,
]

# Turn LVAlert on/off from the environment. Adding this
# to turn lvalerts on/off from docker compose/update instead
# of having to rebuild containers. If the environment variable
# isn't set, then revert to the hardwired behavior:
xmpp_env_var = get_from_env('SEND_LVALERT_XMPP_ALERTS',
                   default_value=SEND_XMPP_ALERTS,
                   fail_if_not_found=False)
# Fix for other boolean values:
if (isinstance(xmpp_env_var, str) and
    xmpp_env_var.lower() in ['true','t','1']):
    SEND_XMPP_ALERTS=True
elif (isinstance(xmpp_env_var, str) and
    xmpp_env_var.lower() in ['false','f','0']):
    SEND_XMPP_ALERTS=False
else:
    SEND_XMPP_ALERTS = True

# Enforce that phone and email alerts are off
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False


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
INSTANCE_TITLE = 'GraceDB Testing Server'
INSTANCE_LIST = INSTANCE_STUB.format(ENABLED[SEND_PHONE_ALERTS],
                                ENABLED[SEND_EMAIL_ALERTS],
                                LVALERT_OVERSEER_INSTANCES[0]['lvalert_server'],
                                ENABLED[SEND_XMPP_ALERTS],
                                LVALERT_OVERSEER_INSTANCES[1]['lvalert_server'],
                                ENABLED[SEND_XMPP_ALERTS])

# Add sub-bullet with igwn-alert group:
if (len(LVALERT_OVERSEER_INSTANCES) == 2):
    igwn_alert_group = os.environ.get('IGWN_ALERT_GROUP', 'lvalert-dev')
    group_sub_bullet = """<ul>
    <li> Messages are sent to group: <span class="text-monospace"> {0}  </span></li>
    </ul>""".format(igwn_alert_group)
    INSTANCE_LIST = INSTANCE_LIST + group_sub_bullet

INSTANCE_INFO = """
<h5>Testing Instance</h5>
<hr>
<p>
This GraceDB instance is designed for Quality Assurance (QA) testing and
validation for GraceDB and electromagnetic follow-up (EMFollow) developers.
Software should meet QA milestones on the test instance before being moved 
to Playground or Production. Note, on this GraceDB instance:
</p>
<ul>
{}
<li>Only LIGO logins are provided (no login via InCommon or Google).</li>
</ul>
""".format(INSTANCE_LIST)

if AWS_ELASTICACHE_ADDR:
    CACHES['default']['KEY_PREFIX'] = '2'
    CACHE_MIDDLEWARE_KEY_PREFIX  = '2'
