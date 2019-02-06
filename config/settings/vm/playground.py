# Settings for a playground GraceDB instance (for user testing) running
# on a VM with Puppet provisioning. Starts with vm.py settings (which inherits
# from base.py settings) and overrides or adds to them.
import textwrap
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

# Define correct LVAlert settings
LVALERT_OVERSEER_INSTANCES = [
    {
        "lvalert_server": "lvalert-playground.cgca.uwm.edu",
        "listen_port": 8001,
    },
]

# Add testserver to ALLOWED_HOSTS
ALLOWED_HOSTS += ['testserver']

# Home page stuff
INSTANCE_TITLE = 'GraceDB Playground'
INSTANCE_INFO = """
<p>
This GraceDB instance is designed for users to develop and test their own
applications. It mimics the production instance in all but the following ways:
</p>
<ul>
<li>Phone and e-mail alerts are turned off</li>
<li>Only LIGO logins are provided (no login via InCommon or Google)</li>
<li>LVAlert messages are sent to lvalert-playground.cgca.uwm.edu</li>
<li>Events and associated data will <b>not</b> be preserved indefinitely.
A nightly cron job removes events older than 14 days.</li>
<li><b>Note:</b> for O3 development, the above number has been updated to
<b>112</b>.</li>
</ul>
"""
