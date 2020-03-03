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

# Turn on XMPP alerts
SEND_XMPP_ALERTS = True

# Enforce that phone and email alerts are off
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Home page stuff
INSTANCE_TITLE = 'GraceDB Playground'
INSTANCE_INFO = """
<h3>Playground instance</h3>
<p>
This GraceDB instance is designed for users to develop and test their own
applications. It mimics the production instance in all but the following ways:
</p>
<ul>
<li>Phone and e-mail alerts are turned off.</li>
<li>Only LIGO logins are provided (no login via InCommon or Google).</li>
<li>LVAlert messages are sent to lvalert-playground.cgca.uwm.edu.</li>
<li>Events and associated data will <b>not</b> be preserved indefinitely.
A nightly cron job removes events older than 21 days.</li>
</ul>
"""

# Safety check on debug mode for playground
if (DEBUG == True):
    raise RuntimeError("Turn off debug mode for playground")

# Set elasticache prefix if the correct variables are set.
if AWS_ELASTICACHE_ADDR:
    CACHES['default']['KEY_PREFIX'] = '3'
    CACHE_MIDDLEWARE_KEY_PREFIX = '3'
