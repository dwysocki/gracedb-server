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

# Enforce that phone and email alerts are off
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Home page stuff
INSTANCE_TITLE = 'GraceDB Playground'

# Add sub-bullet with igwn-alert group:
if (len(LVALERT_OVERSEER_INSTANCES) == 2):
    igwn_alert_group = os.environ.get('IGWN_ALERT_GROUP', 'lvalert-dev')
    group_sub_bullet = """<ul>
    <li> Messages are sent to group: <span class="text-monospace"> {0}  </span></li>
    </ul>""".format(igwn_alert_group)
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

# Set elasticache prefix if the correct variables are set.
if AWS_ELASTICACHE_ADDR:
    CACHES['default']['KEY_PREFIX'] = '3'
    CACHE_MIDDLEWARE_KEY_PREFIX = '3'
