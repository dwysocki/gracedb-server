# XXX I know import * is ugly, but I want the stuff from logSettings to be
# in this namespace.
# from logSettings import *

CONFIG_NAME = "EMBB development"

DEBUG = True
TEMPLATE_DEBUG = DEBUG
# LOG_ROOT = '/home/jkanner/logs'
# LOGGING={}

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'jkanner',
        'PASSWORD' : 'batman',
	'OPTIONS'  : {
		'init_command' : 'SET storage_engine=MyISAM',
		}
    }
}

ROOT_URLCONF = 'urls'

#MEDIA_URL = "/gracedb-static/"

SKYMAP_VIEWER_MEDIA_URL = "/skymap-viewer/"

GRACEDB_DATA_DIR = "/home/roywilliams/gracedbData"
MPLCONFIGDIR = "/home/jkanner/mplconfig"

ALERT_EMAIL_FROM = "Dev Alert <root@embb-dev.ligo.caltech.edu>"
ALERT_EMAIL_TO = [
    "Roy Williams <roy@caltech.edu>",
    ]
ALERT_EMAIL_BCC = ["roy@caltech.edu"]

ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@embb-dev.ligo.caltech.edu>"
ALERT_TEST_EMAIL_TO = [
    "Roy Williams <roy@caltech.edu>",
    ]


EMBB_MAIL_ADDRESS = 'embb@embb-dev.ligo.caltech.edu'
EMBB_SMTP_SERVER = 'acrux.ligo.caltech.edu'
EMBB_MAIL_ADMINS = ['roy.williams@ligo.org',]

BLESSED_TAGS = [
                 'analyst_comments',
                 'psd',
                 'data_quality',
                 'sky_loc',
                 'background',
                 'ext_coinc',
                 'strain',
                 'tfplots',
                 'sig_info',
                 'audio',
               ]


# Don't sent out non-test XMPP alerts on dev box!
XMPP_ALERT_CHANNELS = [
                        'test_omega',
                        'test_mbtaonline',
                        'test_cwb',
                        'test_lowmass',
                      ]
 
# SkyAlert
SKYALERT_IVORN_PATTERN = "ivo://ligo.org/gracedb#%s-dev"

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/jkanner/data/latency"
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/home/jkanner/data/uptime"


#SITE_ID = 4

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/roywilliams/gracedbdev/templates",
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

AUTHENTICATION_BACKENDS = (
#   'gracedb.middleware.auth.LigoAuthBackend',
    'ligoauth.middleware.auth.LigoX509Backend',
    'ligoauth.middleware.auth.LigoShibBackend',
#   'ligoauth.middleware.auth.RemoteUserBackend',
#   'ligodjangoauth.LigoShibbolethAuthBackend',
#   'django.contrib.auth.backends.ModelBackend',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    #"django.core.context_processors.auth",
    # replaced by...
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "gracedb.middleware.auth.LigoAuthContext",
    'middleware.debug.LigoDebugContext',
)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.sites',
    'django.contrib.staticfiles',
    'gracedb',
    'userprofile',
    'ligoauth',
    'rest_framework',
    'south',
#    'debug_toolbar',
)

INTERNAL_IPS = (
    '129.89.61.55',
)


LOGGING = {}
x = """     HACH HACK HACK
LOG_ROOT = '/home/jkanner/logs'
LOG_FILE_SIZE = 1024*1024 # 1 MB
LOG_FILE_BAK_CT = 3

LOGGING = {
    'version': 1,
    'disable_existing_loggers' : True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s: %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'performance_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'filename': '%s/gracedb_performance.log' % LOG_ROOT,
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': True,
            'level': 'INFO',
        },
        'middleware': {
            'handlers': ['performance_file'],
            'propagate': True,
            'level': 'INFO',
        },
   },
}
"""
