from settings_secret import *
# Settings for Logging.
import logging

CONFIG_NAME = "TEST"

# Debug settings
DEBUG = True
# Template debugging help
TEMPLATE_DEBUG = DEBUG
# Don't let debug toolbar edit settings
DEBUG_TOOLBAR_PATCH_SETTINGS = False

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'gracedb',
        'PASSWORD' : TEST_DB_PASSWORD,
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

# Email settings
SERVER_EMAIL = "GraceDB Test <gracedb@gracedb-test.cgca.uwm.edu>"
ALERT_EMAIL_FROM = "GraceDB Test <gracedb@gracedb-test.cgca.uwm.edu>"
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
    'django_twilio',
    #'debug_toolbar',
    #'debug_panel',
)

INTERNAL_IPS = (
    #'129.89.57.72',
    '129.89.57.83',
)

CONTROL_ROOM_IPS = {
    'H1': '108.45.69.217',
    'L1': '129.2.92.124',
#    'L1': '129.89.57.83',
}

# Everything below here is logging. ###########################################

LOG_ROOT = '/home/gracedb/logs'
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
            'format': '%(asctime)s %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
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
