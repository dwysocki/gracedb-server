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

# All alerts off
# TODO: get kafka igwn-alerts working. 
SEND_XMPP_ALERTS = False
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False

# Turn off shibboleth logins on this instance
USE_SHIBBOLETH_LOGIN = True

# Proxy Shibboleth authentication mode
# When True: All requests require Shibboleth auth at Apache level (auto-login)
# When False: Traditional flow with login button at /post-login/
PROXY_SHIBBOLETH_AUTH = True

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
    },
}
