# XXX I know import * is ugly, but I want the stuff from logSettings to be
# in this namespace.
from logSettings import *

CONFIG_NAME = "Branson"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'branson',
        'PASSWORD' : 'thinglet',
    }
}

MEDIA_URL = "/branson-static/"

GRACEDB_DATA_DIR = "/home/branson/fake_data"

ALERT_EMAIL_FROM = "Dev Alert <root@moe.phys.uwm.edu>"
ALERT_EMAIL_TO = [
    "Branson Stephens <branson@gravity.phys.uwm.edu>",
    ]
ALERT_EMAIL_BCC = ["branson@gravity.phys.uwm.edu"]

ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@moe.phys.uwm.edu>"
ALERT_TEST_EMAIL_TO = [
    "Branson Stephens <branson@gravity.phys.uwm.edu>",
    ]

# Don't sent out non-test XMPP alerts on dev box!
XMPP_ALERT_CHANNELS = [
                        'test_omega',
                        'test_mbtaonline',
                        'test_cwb',
                        'test_lowmass',
                      ]
 
# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/branson/data/latency"
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/homebransonbmoe/data/uptime"


SITE_ID = 4

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/branson/gracedbdev/templates",
)

MIDDLEWARE_CLASSES = [
    'middleware.accept.AcceptMiddleware',
    'middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'ligodjangoauth.LigoShibbolethMiddleware',
    'ligoauth.middleware.auth.LigoAuthMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'gracedb',
    'userprofile',
    'ligoauth',
    'rest_framework',
    'south',
    'debug_toolbar',
)

INTERNAL_IPS = (
    '129.89.61.55',
)
