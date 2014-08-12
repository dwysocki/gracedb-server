CONFIG_NAME = "Branson"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default' : {
        'NAME'     : 'guardian',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'branson',
        'PASSWORD' : 'thinglet',
    }
}

MEDIA_URL = "/branson-static/"
STATIC_ROOT = "/home/branson/gracedbdev/static/"

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
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

#INSTALLED_APPS = (
#    'django.contrib.auth',
#    'django.contrib.admin',
#    'django.contrib.contenttypes',
#    'django.contrib.sessions',
#    'django.contrib.sites',
#    'django.contrib.staticfiles',
#    'gracedb',
#    'userprofile',
#    'ligoauth',
#    'rest_framework',
#    'south',
##    'debug_toolbar',
#)

#INTERNAL_IPS = (
#    '129.89.61.55',
#)


# Settings for Logging.
import logging

LOG_ROOT = '/home/branson/logs'
LOG_FILE_SIZE = 1024*1024 # 1 MB
LOG_FILE_BAK_CT = 3
LOG_FORMAT = 'verbose'
LOG_LEVEL = 'DEBUG'

# Filter objects to separate out each level of alert.
# Otherwise the log files for each level would contain the
# output for each higher level.
class debugOnlyFilter(logging.Filter):
    def filter(self,record):
        if record.levelname=='DEBUG':
            return 1
        return 0
class infoOnlyFilter(logging.Filter):
    def filter(self,record):
        if record.levelname=='INFO':
            return 1
        return 0
class debugPlusInfo(logging.Filter):
    def filter(self,record):
        if record.levelname=='INFO' or record.levelname=='DEBUG':
            return 1
        return 0
class warningOnlyFilter(logging.Filter):
    def filter(self,record):
        if record.levelname=='WARNING':
            return 1
        return 0
class errorOnlyFilter(logging.Filter):
    def filter(self,record):
        if record.levelname=='ERROR':
            return 1
        return 0

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
#    'filters': {
#        'debugOnly': {
#            '()': 'settings.logSettings.debugOnlyFilter',
#        },
#        'infoOnly': {
#            '()': 'settings.logSettings.infoOnlyFilter',
#        },
#        'debugPlusInfo': {
#            '()': 'settings.logSettings.debugPlusInfo',
#        },
#        'warningOnly': {
#            '()': 'settings.logSettings.warningOnlyFilter',
#        },
#        'errorOnly': {
#            '()': 'settings.logSettings.errorOnlyFilter',
#        },
#    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'debug_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': LOG_FORMAT,
#           Commented out so that the debug file will have *everything*  
#           That should make it somewhat easier to read through.                        
#            'filters': ['debugPlusInfo'],
            'filename': '%s/gracedb_debug.log' % LOG_ROOT,
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
        },
#        'info_file': {
#            'class': 'logging.handlers.RotatingFileHandler',
#            'formatter': LOG_FORMAT,
#            'filters': ['infoOnly'],
#            'filename': '%s/gracedb_info.log' % LOG_ROOT,
#            'maxBytes': LOG_FILE_SIZE,
#            'backupCount': LOG_FILE_BAK_CT,
#        },
#        'warning_file': {
#            'class': 'logging.handlers.RotatingFileHandler',
#            'formatter': LOG_FORMAT,
#            'filters': ['warningOnly'],
#            'filename': '%s/gracedb_warning.log' % LOG_ROOT,
#            'maxBytes': LOG_FILE_SIZE,
#            'backupCount': LOG_FILE_BAK_CT,
#        },  
#        'error_file': {
#            'class': 'logging.handlers.RotatingFileHandler',
#            'formatter': LOG_FORMAT,
#            'filters': ['errorOnly'],
#            'filename': '%s/gracedb_error.log' % LOG_ROOT,
#            'maxBytes': LOG_FILE_SIZE,
#            'backupCount': LOG_FILE_BAK_CT,
#        },  
       'performance_file': {
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': '%s/gracedb_performance.log' % LOG_ROOT,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': True,
            'level': 'INFO',
        },
        'gracedb': {
#            'handlers': ['debug_file', 'info_file', 'warning_file', 'error_file'],
            'handlers': ['debug_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'middleware': {
            'handlers': ['performance_file'],
            'propagate': True,
            'level': 'INFO',
        }, 
#        'userprofile': {
#            'handlers': ['debug_file', 'info_file', 'warning_file', 'error_file'],
#            'propagate': True,
#            'level': LOG_LEVEL,
#        },
   },
}
