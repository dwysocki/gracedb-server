# Settings for a playground GraceDB instance (for user testing) running
# in a container on AWS. These settings inherent from base.py) 
# and overrides or adds to them.
from .base import *

CONFIG_NAME = "USER TESTING"

# Debug settings
DEBUG = False

# Override EMBB email address
# TP (8 Aug 2017): not sure why?
EMBB_MAIL_ADDRESS = 'gracedb@{fqdn}'.format(fqdn=SERVER_FQDN)

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

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Home page stuff
INSTANCE_TITLE = 'GraceDB Playground'
INSTANCE_LIST = INSTANCE_STUB.format(ENABLED[SEND_PHONE_ALERTS],
                                ENABLED[SEND_EMAIL_ALERTS],
                                LVALERT_OVERSEER_INSTANCES[0]['lvalert_server'],
                                ENABLED[SEND_XMPP_ALERTS])
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

# Set elasticache prefix if the correct variables are set.
if AWS_ELASTICACHE_ADDR:
    CACHES['default']['KEY_PREFIX'] = '3'
    CACHE_MIDDLEWARE_KEY_PREFIX = '3'
