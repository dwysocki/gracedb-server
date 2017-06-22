from .secret import DEFAULT_DB_PASSWORD

CONFIG_NAME = "TEST"

# Debug settings
DEBUG = True
# Don't let debug toolbar edit settings
DEBUG_TOOLBAR_PATCH_SETTINGS = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',

    },
    # this cache backend will be used by django-debug-panel
    'debug-panel': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/debug-panel-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 200
        }
    },
}

# Email settings
SERVER_EMAIL = "GraceDB Test <gracedb@gracedb-test.cgca.uwm.edu>"
ALERT_EMAIL_FROM = SERVER_EMAIL
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = \
    "GraceDB Test TESTING <gracedb@gracedb-test.cgca.uwm.edu>"
ALERT_TEST_EMAIL_TO = []

# LVAlert and LVAlert Overseer settings
ALERT_XMPP_SERVERS = ["lvalert-test.cgca.uwm.edu",]
USE_LVALERT_OVERSEER = True
# For each lvalert server, a separate instance of the lvalert_overseer
# must be running and listening on a distinct port. 
LVALERT_OVERSEER_PORTS = {
    'lvalert-test.cgca.uwm.edu': 8001,
}

EMBB_MAIL_ADDRESS = 'gracedb@gracedb-test.cgca.uwm.edu'
EMBB_SMTP_SERVER = 'localhost'
EMBB_MAIL_ADMINS = ['branson@gravity.phys.uwm.edu',]
EMBB_IGNORE_ADDRESSES = ['Mailer-Daemon@gracedb-test.cgca.uwm.edu',]

# Don't sent out non-test XMPP alerts on dev box!
XMPP_ALERT_CHANNELS = [
                        'test_omega',
                        'test_mbtaonline',
                        'test_cwb',
                        'test_lowmass',
                      ]
 
MIDDLEWARE_CLASSES = [
    'middleware.performance.PerformanceMiddleware',
    'middleware.accept.AcceptMiddleware',
    'middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'ligoauth.middleware.auth.LigoAuthMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    #'debug_panel.middleware.DebugPanelMiddleware',
    #'middleware.profiling.ProfileMiddleware',
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'gracedb',
    'userprofile',
    'ligoauth',
    'rest_framework',
    'guardian',
    'django_twilio',
    #'debug_toolbar',
    #'debug_panel',
)

INTERNAL_IPS = (
    '129.89.57.83',
)

# Use these to test operator signoffs
# Change to your own IP.
CONTROL_ROOM_IPS = {
    'H1': '108.45.69.217',
    'L1': '129.2.92.124',
    'V1': '90.147.136.220',
}

