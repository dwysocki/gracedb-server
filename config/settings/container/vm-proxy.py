# Settings for a containerized GraceDB instance for local and
# end-to-end testing. This should *NEVER* be used for a real
# deployment.
from .base import *
import socket


# Config name
TIER = 'proxy'
CONFIG_NAME = get_from_env('CONFIG_NAME', fail_if_not_found=False,
        default_value='VM PROXY')

# Debug settings
DEBUG = True

# All notifications off
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False

# Turn off shibboleth logins on this instance
USE_SHIBBOLETH_LOGIN = True

# Proxy Shibboleth authentication mode
# When True: All requests require Shibboleth auth at Apache level (auto-login)
# When False: Traditional flow with login button at /post-login/
PROXY_SHIBBOLETH_AUTH = True

# Shibboleth header names for proxy mode
# Apache mod_shib typically forwards these with HTTP_SHIB_ prefix
SHIB_GROUPS_HEADER = get_from_env('SHIB_GROUPS_HEADER', fail_if_not_found=False,
        default_value='HTTP_SHIB_ISMEMBEROF')

# FQDN of service
#LIGO_FQDN = get_from_env('LIGO_FQDN', fail_if_not_found=False,
#        default_value=socket.getfqdn())
HTTP_PORT = get_from_env('SERVICE_PORT', fail_if_not_found=False)

# Allowed hosts
#ALLOWED_HOSTS = ['localhost', '127.0.0.1', LIGO_FQDN]
CSRF_TRUSTED_ORIGINS = ['https://' + host for host in ALLOWED_HOSTS]

# Adjust ADMINS for dev instances
ADMINS = []

# Use HTTP
USE_HTTP = False

# Turn off requirement for session cookie to require HTTPS
# NOT SAFE FOR A REAL DEPLOYMENT!
SESSION_COOKIE_SECURE = True

# Keep Shibboleth middleware/auth backends for proxy auth mode
# NOTE: Previously these were removed, but proxy auth requires them
# shib_middleware = 'ligoauth.middleware.ShibbolethWebAuthMiddleware'
# if shib_middleware in MIDDLEWARE:
#     MIDDLEWARE.remove(shib_middleware)
# shib_auth_backend = 'ligoauth.backends.ShibbolethRemoteUserBackend'
# if shib_auth_backend in AUTHENTICATION_BACKENDS:
#     AUTHENTICATION_BACKENDS.remove(shib_auth_backend)

# Things that should be secret, but it doesn't matter for a container that
# people are going to use for local testing.

# We need to set these just to get things to work
TWILIO_ACCOUNT_SID = 'FAKE_TWILIO_ACCOUNT_SID'
TWILIO_AUTH_TOKEN = 'FAKE_TWILIO_AUTH_TOKEN'

# SECRET_KEY must be set in environment
SECRET_KEY = get_from_env('DJANGO_SECRET_KEY', fail_if_not_found=True)

# Database settings - use PostgreSQL for local container
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_from_env('POSTGRES_DB', fail_if_not_found=False, default_value='gracedb'),
        'USER': get_from_env('POSTGRES_USER', fail_if_not_found=False, default_value='gracedb_user'),
        'PASSWORD': get_from_env('POSTGRES_PASSWORD', fail_if_not_found=False, default_value='gracedb_password'),
        'HOST': get_from_env('POSTGRES_HOST', fail_if_not_found=False, default_value='postgres'),
        'PORT': get_from_env('POSTGRES_PORT', fail_if_not_found=False, default_value='5432'),
        'OPTIONS': {
            'options': f'-c random_page_cost={PSQL_RANDOM_PAGE_COST}'
        },
    },
}

# Home page stuff
INSTANCE_TITLE = get_from_env('INSTANCE_TITLE', fail_if_not_found=False,
        default_value='MDC/LLPIC Validation Instance')

# Add sub-bullet with igwn-alert group:
group_sub_bullet = """<ul>
<li> Messages are sent to group: <span class="text-monospace"> {0}  </span></li>
</ul>""".format(LVALERT_OVERSEER_INSTANCES[0]['igwn_alert_group'])
INSTANCE_LIST = INSTANCE_LIST + group_sub_bullet

INSTANCE_LIST += """
<li>Uptime and data retention are handled on a best-effort basis</li>
"""

INSTANCE_INFO = f"""
<h5>{INSTANCE_TITLE}</h5>
<hr>
<p>
This GraceDB instance is a stand-alone virtual machine (VM) hosted at Caltech
used for pipeline review and MDC/LLPIC purposes. This instance's uptime is
handled on a best-effort basis, and does not have the guaranteed uptime of a
full high-availability cloud deployment. Please make an issue on the
<a href="https://git.ligo.org/computing/helpdesk/-/issues">IGWN Gitlab Helpdesk</a>
if you encounter any issues. Note, on this GraceDB instance:
</p>
<ul>
{INSTANCE_LIST}
</ul>
"""
