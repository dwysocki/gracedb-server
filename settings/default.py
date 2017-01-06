from settings_secret import *
from utils import posixToGpsTime
from datetime import datetime, timedelta
import time
import logging

USE_TZ = True

# Suitable for production
ALLOWED_HOSTS = ['*']

DEBUG = False
TEMPLATE_DEBUG = DEBUG
MAINTENANCE_MODE = False

ADMINS = (
    ('Alexander Pace', 'aep14@psu.edu'),
    ('Tanner Prestegard', 'tanner.prestegard@ligo.org'),
)
MANAGERS = ADMINS

# Base URL for TwiML bins
TWIML_BASE_URL = 'https://handler.twilio.com/twiml/'

# Email settings.
#EMAIL_HOST = 'gravity.phys.uwm.edu'
EMAIL_HOST = 'localhost'
SERVER_EMAIL = 'GraceDB <gracedb@gracedb.cgca.uwm.edu>'
ALERT_EMAIL_FROM = SERVER_EMAIL
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = "GraceDB TESTING <gracedb@gracedb.cgca.uwm.edu>"
ALERT_TEST_EMAIL_TO = []

# LVAlert and LVAlert Overseer settings
LVALERT_SEND_EXECUTABLE = '/home/gracedb/djangoenv/bin/lvalert_send'
ALERT_XMPP_SERVERS = ["lvalert.cgca.uwm.edu"]
USE_LVALERT_OVERSEER = True
# For each lvalert server, a separate instance of the lvalert_overseer
# must be running and listening on a distinct port. 
LVALERT_OVERSEER_PORTS = {
    'lvalert.cgca.uwm.edu': 8000,
}

EMBB_MAIL_ADDRESS = 'embb@gracedb.ligo.org'
EMBB_SMTP_SERVER = 'localhost'
EMBB_MAIL_ADMINS = ['branson@gravity.phys.uwm.edu','roy.williams@ligo.org',]
EMBB_IGNORE_ADDRESSES = ['Mailer-Daemon@gracedb.cgca.uwm.edu',]

# Added for django 1.7.8
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Some proper names related to authorization
LVC_GROUP = 'Communities:LSCVirgoLIGOGroupMembers'
LVEM_GROUP = 'gw-astronomy:LV-EM'
LVEM_OBSERVERS_GROUP = 'gw-astronomy:LV-EM:Observers'
# Executives
EXEC_GROUP = 'executives'
# EM Advocate Group name
EM_ADVOCATE_GROUP = 'em_advocates'

# Groups directly managed by GraceDB admins
ADMIN_MANAGED_GROUPS = [EM_ADVOCATE_GROUP, 'executives',]

EXTERNAL_ACCESS_TAGNAME = 'lvem'

# FAR floor for outgoing VOEvents intended for GCN
#VOEVENT_FAR_FLOOR = 3.17e-10 # 1/100 yrs
VOEVENT_FAR_FLOOR = 0

# URL for viewing skymaps
SKYMAP_VIEWER_SERVICE_URL = \
    "https://embb-dev.ligo.caltech.edu/skymap-viewer/aladin/skymap-viewer.cgi"

# Log entries with these tags are displayed in
# their own blocks in the web interface.
BLESSED_TAGS = [
                 'analyst_comments',
                 'em_follow',
                 'psd',
                 'data_quality',
                 'sky_loc',
                 'background',
                 'ext_coinc',
                 'strain',
                 'tfplots',
                 'pe',
                 'sig_info',
                 'audio',
               ]

COINC_PIPELINES = [
                    'gstlal',
                    'gstlal-spiir',
                    'MBTAOnline',
                    'pycbc',
                   ]

GRB_PIPELINES = [
                    'Fermi',
                    'Swift',
                ]

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'gracedb',
        'PASSWORD' : DEFAULT_DB_PASSWORD,
        'OPTIONS'  : {
                         'init_command': 'SET storage_engine=MyISAM',
                     },
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# SkyAlert
SKYALERT_IVORN_PATTERN = "ivo://gwnet/gcn_sender#%s"
SKYALERT_ROLE          = "test"
SKYALERT_DESCRIPTION   = "Report of a candidate gravitational wave event"
SKYALERT_SUBMITTERS = ['Patrick Brady', 'Brian Moe']

# Location of database
GRACEDB_DATA_DIR = "/opt/gracedb/data"
# First level subdirs with 2 chars, second level with 1 char
# These DIR_DIGITS had better add up to a number less than 40 (which is
# the length of a SHA-1 hexdigest. Actually, it should be way less than
# 40--or you're a crazy person.
GRACEDB_DIR_DIGITS = [2, 1,]

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/gracedb/data/latency"
LATENCY_MAXIMUM_CHARTED = 1800
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/home/gracedb/data/uptime"

# Rate file location
RATE_INFO_FILE = "/home/gracedb/data/rate_info.json"

# URL prefix for serving report information (usually plots and tables)
REPORT_INFO_URL_PREFIX = "/report_info/"

# Find another way to do this.
#
# CBC IFAR Reports

now = datetime.now()
yesterday = now - timedelta(days=1)
lastweek = now - timedelta(days=7)
now = posixToGpsTime(time.mktime(now.timetuple()))
yesterday = posixToGpsTime(time.mktime(yesterday.timetuple()))
lastweek = posixToGpsTime(time.mktime(lastweek.timetuple()))

REPORT_IFAR_IMAGE_DIR = LATENCY_REPORT_DEST_DIR
#REPORTS_IFAR = [
#    #(query, axis_label, title, fname),
#    ("LowMass %d..%d" % (yesterday, now),
#     "GraceDB CBC LowMass ER1 events",
#     "ER1 FARs from gstlal_ll_inspiral - last day",
#     "ifar_day.png"
#    ),
#    ("LowMass %d..%d" % (lastweek, now),
#     "GraceDB CBC LowMass ER1 events",
#     "ER1 FARs from gstlal_ll_inspiral - last week",
#     "ifar_week.png"
#    ),
#]
REPORTS_IFAR = [
    #(query, axis_label, title, fname),
    ("gstlal %d..%d" % (yesterday, now),
     "GraceDB gstlal events",
     "FARs from gstlal - last day",
     "ifar_day.png"
    ),
    ("gstlal %d..%d" % (lastweek, now),
     "GraceDB gstlal events",
     "FARs from gstlal - last week",
     "ifar_week.png"
    ),
]

# Stuff for the new rates plot
BINNED_COUNT_PIPELINES = ['gstlal', 'MBTAOnline', 'CWB', 'LIB', 'gstlal-spiir']
BINNED_COUNT_FILE = "/home/gracedb/data/binned_counts.json"

# Whether or not to show the recent events on the landing page
SHOW_RECENT_EVENTS_ON_HOME = False

# RSS Feed Defaults
FEED_MAX_RESULTS = 50

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'
GRACE_DATETIME_FORMAT = 'Y-m-d H:i:s T'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
#MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
#MEDIA_URL = '/gracedb-static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = DEFAULT_SECRET_KEY

# New template settings compatible with Django 1.8
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            '/home/gracedb/gracedb/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Defaults
                'django.contrib.auth.context_processors.auth',
                'django.core.context_processors.debug',
                'django.core.context_processors.i18n',
                'django.core.context_processors.media',
                'django.core.context_processors.static',
                # Extra additions
                'django.core.context_processors.request',
                'gracedb.middleware.auth.LigoAuthContext',
                'middleware.debug.LigoDebugContext',
                'ligoauth.context_processors.shib_login_url',
            ],
        },
    },
]


AUTHENTICATION_BACKENDS = (
#   'gracedb.middleware.auth.LigoAuthBackend',
    'ligoauth.middleware.auth.LigoX509Backend',
    'ligoauth.middleware.auth.LigoShibBackend',
    'ligoauth.middleware.auth.LigoBasicBackend',
    'ligoauth.middleware.auth.ModelBackend',
#   'ligoauth.middleware.auth.RemoteUserBackend',
#   'ligodjangoauth.LigoShibbolethAuthBackend',
#   'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

ANONYMOUS_USER_ID = -1
GUARDIAN_RENDER_403 = True
GUARDIAN_MONKEY_PATCH = False

# URL of Shibboleth login page
LOGIN_URL = '/Shibboleth.sso/Login'

# If these are left at default, when the Shibboleth middleware
# creates a new auth_user, they will get admin privs.
ADMIN_GROUP_HEADER = None
ADMIN_GROUP = None

MIDDLEWARE_CLASSES = [
    'middleware.performance.PerformanceMiddleware',
    'middleware.accept.AcceptMiddleware',
    'middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#   'django.contrib.auth.middleware.AuthenticationMiddleware',
#   'ligodjangoauth.LigoShibbolethMiddleware',
    'ligoauth.middleware.auth.LigoAuthMiddleware',
#   'django.contrib.auth.middleware.RemoteUserMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
]

ROOT_URLCONF = 'urls'

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
    'guardian',
    'django_twilio',
)

REST_FRAMEWORK = {
    'PAGINATE_BY': 10,
    'DEFAULT_THROTTLE_RATES': {
        'event_creation': '1/second',
        'annotation'    : '10/second',
    },
}

# Location of static components, CSS, JS, etc.
STATIC_URL = "/gracedb-static/"
STATIC_ROOT = "/home/gracedb/gracedb/static/"
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)
STATICFILES_DIRS = ()

# Location of Bower packages.
BOWER_URL = "/bower-static/"
BOWER_ROOT = "/home/gracedb/bower_components/"

# Added in order to perform data migrations on the auth app
MIGRATION_MODULES = {
    'auth' : 'migrations.auth',
    'guardian' : 'migrations.guardian',
}

SOUTH_TESTS_MIGRATE = False

# Passwords for LVEM scripted access expire after 365 days.
PASSWORD_EXPIRATION_TIME = timedelta(days=365)

# LIGO control room IPs
CONTROL_ROOM_IPS = {
    'H1': '198.129.208.178',
    'L1': '208.69.128.41',
}

# Everything below here is logging. ###########################################

# Filter objects to separate out each level of alert.
# Currently unused (TP 1/6/2017)
class infoOnlyFilter(logging.Filter):
    def filter(self,record):
        if record.levelname=='INFO':
            return 1
        return 0

LOG_ROOT = '/home/gracedb/logs'
LOG_FILE_SIZE = 1024*1024 # 1 MB
LOG_FILE_BAK_CT = 10
LOG_FORMAT = 'extra_verbose'
LOG_LEVEL = 'DEBUG'

# Note that mode for log files is 'a' (append) by default
# The 'level' specifier on the handle is optional, and we
# don't need it since we're using custom filters.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'verbose': {
            'format': '%(asctime)s | %(name)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'extra_verbose': {
            'format': '%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | ' \
                      + '%(filename)s, line %(lineno)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'debug_file': {
            'class': 'logging.handlers.ConcurrentRotatingFileHandler',
            'formatter': LOG_FORMAT,
            'filename': '%s/gracedb_debug.log' % LOG_ROOT,
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
            'level': 'DEBUG',
        },
        'info_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'simple',
            'filename': '%s/gracedb_info.log' % LOG_ROOT,
            'when': 'midnight',
            'backupCount': LOG_FILE_BAK_CT,
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.handlers.ConcurrentRotatingFileHandler',
            'formatter': LOG_FORMAT,
            'filename': '%s/gracedb_error.log' % LOG_ROOT,
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
            'level': 'ERROR',
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
            'handlers': ['debug_file','info_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'ligoauth': {
            'handlers': ['debug_file','info_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'userprofile': {
            'handlers': ['debug_file','info_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'middleware': {
            'handlers': ['performance_file'],
            'propagate': True,
            'level': 'INFO',
        },
       'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
   },
}
 
