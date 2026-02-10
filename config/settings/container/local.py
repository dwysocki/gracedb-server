# Settings for a containerized GraceDB instance for local and
# end-to-end testing. This should *NEVER* be used for a real
# deployment.
from .base import *


# Config name
TIER = 'local'
CONFIG_NAME = "LOCAL DEV"

# Debug settings
DEBUG = True

# All alerts off
# TODO: get kafka igwn-alerts working. 
SEND_XMPP_ALERTS = False
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False

# Turn off shibboleth logins on this instance
USE_SHIBBOLETH_LOGIN = False

# Allowed hosts
ALLOWED_HOSTS += ['localhost', '127.0.0.1']

# Adjust ADMINS for dev instances
ADMINS = []

# Use HTTP
USE_HTTP = True

# FQDN of service
LIGO_FQDN = 'localhost'
HTTP_PORT = get_from_env('SERVICE_PORT', fail_if_not_found=False)

# Turn off requirement for session cookie to require HTTPS
# NOT SAFE FOR A REAL DEPLOYMENT!
SESSION_COOKIE_SECURE = False

# Use password-based login
USE_SHIBBOLETH_LOGIN = False

# Remove unnecessary, Shibboleth-related middleware/auth backends
shib_middleware = 'ligoauth.middleware.ShibbolethWebAuthMiddleware'
if shib_middleware in MIDDLEWARE:
    MIDDLEWARE.remove(shib_middleware)
shib_auth_backend = 'ligoauth.backends.ShibbolethRemoteUserBackend'
if shib_auth_backend in AUTHENTICATION_BACKENDS:
    AUTHENTICATION_BACKENDS.remove(shib_auth_backend)

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
