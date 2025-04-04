# Settings for a playground GraceDB instance (for user testing) running
# in a container on AWS. These settings inherent from base.py) 
# and overrides or adds to them.
from .base import *

TIER = "playground"
CONFIG_NAME = "USER TESTING"

# Debug settings
DEBUG = False

# Override EMBB email address
# TP (8 Aug 2017): not sure why?
EMBB_MAIL_ADDRESS = 'gracedb@{fqdn}'.format(fqdn=SERVER_FQDN)

# Enforce that phone and email alerts are off XXX: Set by deployment variables!
#SEND_PHONE_ALERTS = False
#SEND_EMAIL_ALERTS = False

# Enable Mattermost alerts
SEND_MATTERMOST_ALERTS = True

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Set up Sentry for error logging
sentry_dsn = get_from_env('DJANGO_SENTRY_DSN', fail_if_not_found=False)
# Set up sentry tracing:
sentry_tracing = float(get_from_env('DJANGO_SENTRY_TRACES', fail_if_not_found=False,
                     default_value=0.0))
if sentry_dsn is not None:
    USE_SENTRY = True

    # Set up Sentry
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_init_kwargs = {
        'environment': 'playground',
        'dsn': sentry_dsn,
        'integrations': [DjangoIntegration()],
        'before_send': before_send,
    }

    if bool(sentry_tracing):
        sentry_init_kwargs.update({'traces_sample_rate': sentry_tracing})

    sentry_sdk.init(**sentry_init_kwargs)

    # Turn off default admin error emails
    LOGGING['loggers']['django.request']['handlers'] = []

# Home page stuff
INSTANCE_TITLE = 'GraceDB Playground'

# Add sub-bullet with igwn-alert group:
group_sub_bullet = """<ul>
<li> Messages are sent to group: <span class="text-monospace"> {0}  </span></li>
</ul>""".format(LVALERT_OVERSEER_INSTANCES[0]['igwn_alert_group'])
INSTANCE_LIST = INSTANCE_LIST + group_sub_bullet

INSTANCE_INFO = """
<h5>Playground instance</h5>
<hr>
<p>
This GraceDB instance is designed for users to develop and test their own
applications. It mimics the production instance in all but the following ways:
</p>
<ul>
{}
<li>Only LIGO logins are provided (no login via InCommon or Google).</li>
<li>Events and associated data will <b>not</b> be preserved indefinitely.
A nightly cron job removes events older than 21 days.</li>
</ul>
""".format(INSTANCE_LIST)

# Safety check on debug mode for playground
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for playground")
