CONFIG_NAME = "Test"

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEBUG_TOOLBAR_PATCH_SETTINGS = False

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'gracedb',
        'PASSWORD' : 'thinglet',
        'OPTIONS'  : {
            'init_command' : 'SET storage_engine=MYISAM',
        },
    }
}

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

STATIC_URL = "/gracedb-static/"
STATIC_ROOT = "/home/branson.stephens/gracedb/static/"

BOWER_URL = "/bower-static/"
BOWER_ROOT = "/home/branson.stephens/bower_components/"

GRACEDB_DATA_DIR = "/exports/gracedb/data"

EMAIL_HOST = 'localhost'

ALERT_EMAIL_FROM = "Dev Alert <root@gracedb-test.cgca.uwm.edu>"
#ALERT_EMAIL_TO = [
#    "Branson Stephens <branson@gravity.phys.uwm.edu>",
#    ]
#ALERT_EMAIL_BCC = ["branson@gravity.phys.uwm.edu"]
#
#ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@gracedb-test.cgca.uwm.edu>"
#ALERT_TEST_EMAIL_TO = [
#    "Branson Stephens <branson@gravity.phys.uwm.edu>",
#    ]
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@gracedb-test.cgca.uwm.edu>"
ALERT_TEST_EMAIL_TO = []
ALERT_XMPP_SERVERS = ["lvalert-test.cgca.uwm.edu",]

LVALERT_SEND_EXECUTABLE = '/home/branson.stephens/djangoenv/bin/lvalert_send'

USE_LVALERT_OVERSEER = True

# For each lvalert server, a separate instance of the lvalert_overseer
# must be running and listening on a distinct port. 
LVALERT_OVERSEER_PORTS = {
    'lvalert-test.cgca.uwm.edu': 8001,
}

EMBB_MAIL_ADDRESS = 'branson.stephens@gracedb-test.cgca.uwm.edu'
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
 
# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/exports/gracedb/latency"
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/exports/gracedb/uptime"

# Rate file location
RATE_INFO_FILE = "/exports/gracedb/rate_info.json"

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/branson.stephens/gracedb/templates",
)

MIDDLEWARE_CLASSES = [
    'middleware.accept.AcceptMiddleware',
    'middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'ligoauth.middleware.auth.LigoAuthMiddleware',
    'middleware.performance.PerformanceMiddleware',
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
    #'debug_toolbar',
    #'debug_panel',
)

INTERNAL_IPS = (
    '129.89.57.83',
)

CONTROL_ROOM_IPS = {
    'H1': '108.45.69.217',
    'L1': '129.2.92.124',
#    'L1': '129.89.57.83',
}

# Settings for Logging.
import logging

LOG_ROOT = '/home/branson.stephens/logs'
LOG_FILE_SIZE = 1024*1024 # 1 MB
LOG_FILE_BAK_CT = 3
LOG_FORMAT = 'verbose'
LOG_LEVEL = 'DEBUG'

# Note that mode for log files is 'a' (append) by default
# The 'level' specifier on the handle is optional, and we
# don't need it since we're using custom filters.
LOGGING = {
    'version': 1,
    'disable_existing_loggers' : True,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
        'verbose': {
            'format': '%(asctime)s: %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'debug_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': LOG_FORMAT,
            'filename': '%s/gracedb_debug.log' % LOG_ROOT,
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
        },
       'performance_file': {
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': '%s/gracedb_performance.log' % LOG_ROOT,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': True,
            'level': 'INFO',
        },
        'gracedb': {
            'handlers': ['debug_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'ligoauth': {
            'handlers': ['debug_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'middleware': {
            'handlers': ['performance_file'],
            'propagate': True,
            'level': 'INFO',
        }, 
        'userprofile': {
            'handlers': ['debug_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },       
   },
}
