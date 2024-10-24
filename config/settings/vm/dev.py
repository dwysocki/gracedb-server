# Settings for a test/dev GraceDB instance running on a VM with Puppet
# provisioning. Starts with vm.py settings (which inherits from base.py
# settings) and overrides or adds to them.
import socket
from .base import *

TIER = "dev"
CONFIG_NAME = "DEV"

# Debug settings
DEBUG = True
SEND_XMPP_ALERTS=True
SEND_MATTERMOST_ALERTS=True

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
INSTANCE_TITLE = 'GraceDB Development VM'

# Add sub-bullet with igwn-alert group:
if (len(LVALERT_OVERSEER_INSTANCES) == 2):
    igwn_alert_group = os.environ.get('IGWN_ALERT_GROUP', 'lvalert-dev')
    group_sub_bullet = """<ul>
    <li> Messages are sent to group: <span class="text-monospace"> {0}  </span></li>
    </ul>""".format(igwn_alert_group)
    INSTANCE_LIST = INSTANCE_LIST + group_sub_bullet

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
{}
<li>Only LIGO logins are provided (no login via InCommon or Google).</li>
</ul>
""".format(INSTANCE_LIST)

# Turn off public page caching for development and testing:
PUBLIC_PAGE_CACHING = 0

# Hardcode pipelines not approved for production (for vm testing)
# UNAPPROVED_PIPELINES += ['aframe', 'GWAK']
