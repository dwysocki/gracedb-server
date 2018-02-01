import os, time, logging
from os.path import abspath, dirname, join
from datetime import datetime, timedelta
from cloghandler import ConcurrentRotatingFileHandler
from core.time_utils import posixToGpsTime

# Get local settings:
# SERVER_HOSTNAME, SERVER_FQDN, IS_PRODUCTION_SERVER, ADMINS, GRACEDB_PATHS
from .local import *
# Get secret settings:
# DEFAULT_DB_PASSWORD, DEFAULT_SECRET_KEY, TWILIO_ACCOUNT_SID,
# TWILIO_AUTH_TOKEN, TWIML_BIN
from .secret import *

# Set up path to root of project
BASE_DIR = abspath(join(dirname(__file__), "..", ".."))
CONFIG_ROOT = join(BASE_DIR, "config")
PROJECT_ROOT = join(BASE_DIR, "gracedb")

# Miscellaneous settings ------------------------------------------------------
# Debug mode is off by default
DEBUG = False

# Maintenance mode: used by django-maintenance-mode package.
# Set to off by default
MAINTENANCE_MODE = False

# Used for running unit tests
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# ADMINS defines who gets code error notifications.
# MANAGERS defines who gets broken link notifications when
# BrokenLinkEmailsMiddleware is enabled
MANAGERS = ADMINS

# Use forwarded host header for Apache -> Gunicorn reverse proxy configuration
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Base URL for TwiML bins (for Twilio phone/text alerts)
TWIML_BASE_URL = 'https://handler.twilio.com/twiml/'

# Use timezone-aware datetimes internally
USE_TZ = True

# Allow this site to be served on localhost, the FQDN of this server, and
# hostname.ligo.org. Security measure for preventing cache poisoning and
# stopping requests submitted with a fake HTTP Host header.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', SERVER_FQDN,
    '{0}.ligo.org'.format(SERVER_HOSTNAME)]

# LVAlert and LVAlert Overseer settings ---------------------------------------
# Switches which control whether alerts are sent out
SEND_XMPP_ALERTS = False
SEND_PHONE_ALERTS = False
SEND_EMAIL_ALERTS = False
# Use LVAlert Overseer?
USE_LVALERT_OVERSEER = True
# LVAlert servers
ALERT_XMPP_SERVERS = ["lvalert-test.cgca.uwm.edu"]
# For each LVAlert server, a separate instance of LVAlert Overseer
# must be running and listening on a distinct port.
LVALERT_OVERSEER_PORTS = {
    "lvalert-test.cgca.uwm.edu": 8001,
}
# Path to lvalert_send executable, for failover in case
# LVAlert Overseer is not running.
LVALERT_SEND_EXECUTABLE = join(GRACEDB_PATHS["virtualenv"], "bin",
    "lvalert_send")

# Email settings --------------------------------------------------------------
EMAIL_HOST = 'localhost'
SERVER_EMAIL = 'GraceDB <gracedb@{fqdn}>'.format(fqdn=SERVER_FQDN)
ALERT_EMAIL_FROM = SERVER_EMAIL
ALERT_EMAIL_TO = []
ALERT_EMAIL_BCC = []
ALERT_TEST_EMAIL_FROM = SERVER_EMAIL
ALERT_TEST_EMAIL_TO = []
# EMBB email settings
EMBB_MAIL_ADDRESS = 'embb@{fqdn}.ligo.org'.format(fqdn=SERVER_FQDN)
EMBB_SMTP_SERVER = 'localhost'
EMBB_MAIL_ADMINS = [admin[1] for admin in ADMINS]
EMBB_IGNORE_ADDRESSES = ['Mailer-Daemon@{fqdn}'.format(fqdn=SERVER_FQDN)]

# Access and authorization ----------------------------------------------------
# Some proper names related to authorization
LVC_GROUP = 'Communities:LSCVirgoLIGOGroupMembers'
LVEM_GROUP = 'gw-astronomy:LV-EM'
LVEM_OBSERVERS_GROUP = 'gw-astronomy:LV-EM:Observers'
# Executives group name
EXEC_GROUP = 'executives'
# EM Advocate group name
EM_ADVOCATE_GROUP = 'em_advocates'

# Groups directly managed by GraceDB admins
ADMIN_MANAGED_GROUPS = [EM_ADVOCATE_GROUP, 'executives']

# Tag to apply to log messages to allow EM partners to view
EXTERNAL_ACCESS_TAGNAME = 'lvem'

# FAR floor for outgoing VOEvents intended for GCN
VOEVENT_FAR_FLOOR = 0 # Hz

# Web interface settings ------------------------------------------------------

# Whether or not to show the recent events on the  page
# Note that this does NOT filter events based on user view permissions,
# so be careful if you turn it on!
SHOW_RECENT_EVENTS_ON_HOME = False

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

# Lists of pipelines used for selecting templates to serve
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

# SkyAlert stuff - used for VOEvents (?) --------------------------------------
SKYALERT_IVORN_PATTERN = "ivo://gwnet/gcn_sender#%s"
SKYALERT_ROLE          = "test"
SKYALERT_DESCRIPTION   = "Report of a candidate gravitational wave event"
SKYALERT_SUBMITTERS = ['Patrick Brady', 'Brian Moe']

# Stuff related to report/plot generation -------------------------------------

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = GRACEDB_PATHS["latency"]
LATENCY_MAXIMUM_CHARTED = 1800
LATENCY_REPORT_WEB_PAGE_FILE_PATH = join(LATENCY_REPORT_DEST_DIR,
    "latency.inc")

# Uptime reporting
UPTIME_REPORT_DIR = GRACEDB_PATHS["uptime"]

# Rate file location
RATE_INFO_FILE = join(GRACEDB_PATHS["data"], "rate_info.json")

# URL prefix for serving report information (usually plots and tables)
# This is aliased to GRACEDB_PATHS["latency"] in the Apache virtualhost
# configuration.  If you change this, you will need to change that.
REPORT_INFO_URL_PREFIX = "/report_info/"

# Directory for CBC IFAR Reports
REPORT_IFAR_IMAGE_DIR = GRACEDB_PATHS["latency"]

# Stuff for the new rates plot
BINNED_COUNT_PIPELINES = ['gstlal', 'MBTAOnline', 'CWB', 'LIB', 'gstlal-spiir']
BINNED_COUNT_FILE = join(GRACEDB_PATHS["data"], "binned_counts.json")

# Defaults for RSS feed
FEED_MAX_RESULTS = 50

# Django and server settings --------------------------------------------------

# Nested dict of settings for all databases
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

# Location of database
GRACEDB_DATA_DIR = GRACEDB_PATHS["database_data"]
# First level subdirs with 2 chars, second level with 1 char
# These DIR_DIGITS had better add up to a number less than 40 (which is
# the length of a SHA-1 hexdigest. Actually, it should be way less than
# 40--or you're a crazy person.
GRACEDB_DIR_DIGITS = [2, 1,]

# Cache settings - nested dictionary where each element maps
# cache aliases to a dictionary of options for an individual cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# Secret key for a Django installation
# Make this unique, and don't share it with anybody.
SECRET_KEY = DEFAULT_SECRET_KEY

# List of settings for all template engines. Each item is a dict
# containing options for an individual engine
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(PROJECT_ROOT, "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Defaults
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                # Extra additions
                'django.template.context_processors.request',
                'events.context_processors.LigoAuthContext',
                'core.context_processors.LigoDebugContext',
                'ligoauth.context_processors.shib_login_url',
            ],
        },
    },
]

# List of authentication backends to use when attempting to authenticate
# a user.  Will be used in this order
AUTHENTICATION_BACKENDS = (
#   'events.middleware.auth.LigoAuthBackend',
    'ligoauth.middleware.auth.LigoX509Backend',
    'ligoauth.middleware.auth.LigoShibBackend',
    'ligoauth.middleware.auth.LigoBasicBackend',
    'ligoauth.middleware.auth.ModelBackend',
#   'ligoauth.middleware.auth.RemoteUserBackend',
#   'ligodjangoauth.LigoShibbolethAuthBackend',
#   'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# List of middleware classes to use.
MIDDLEWARE = [
    'events.middleware.PerformanceMiddleware',
    'core.middleware.accept.AcceptMiddleware',
    'core.middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'ligoauth.middleware.auth.LigoAuthMiddleware',
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
]

# Path to root URLconf
ROOT_URLCONF = '{module}.urls'.format(module=os.path.basename(CONFIG_ROOT))

# List of string designating all applications which are enabled.
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.sites',
    'django.contrib.staticfiles',
    'maintenance_mode',
    'events',
    'userprofile',
    'ligoauth',
    'rest_framework',
    'guardian',
    'django_twilio',
]

# Details used by REST API
REST_FRAMEWORK = {
    'PAGINATE_BY': 10,
    'DEFAULT_THROTTLE_RATES': {
        'event_creation': '1/second',
        'annotation'    : '10/second',
    },
}

# Location of static components, CSS, JS, etc.
STATIC_ROOT = join(PROJECT_ROOT, "static/")
STATIC_URL = "/gracedb-static/"
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
]
STATICFILES_DIRS = []

# Location of Bower packages.
BOWER_URL = "/bower-static/"
BOWER_ROOT = join(GRACEDB_PATHS["home"], "bower_components/")

# Added in order to perform data migrations on the auth and guardian apps
MIGRATION_MODULES = {
    'auth': 'migrations.auth',
    'guardian': 'migrations.guardian',
}

# Forces test database to be created with syncdb rather than via
# migrations in South.
# TP (8 Aug 2017): not sure this is used anymore
SOUTH_TESTS_MIGRATE = False

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment, this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'
GRACE_DATETIME_FORMAT = 'Y-m-d H:i:s T'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# django-guardian configuration
# Note for upgrading: ANONYMOUS_USER_ID becomes ANONYMOUS_DEFAULT_USERNAME
# and USERNAME_FIELD in django-guardian 1.4.2
ANONYMOUS_USER_ID = -1
# Have guardian try to render a 403 response rather than return
# a contentless django.http.HttpResponseForbidden. Should set
# GUARDIAN_TEMPLATE_403 to a template to be used by this.
GUARDIAN_RENDER_403 = True
# Used by guardian for dealing with errors related to the user model
# See http://django-guardian.readthedocs.io/en/latest/userguide/custom-user-model.html
GUARDIAN_MONKEY_PATCH = False

# URL of Shibboleth login page
LOGIN_URL = '/Shibboleth.sso/Login'

# If these are left at default, when the Shibboleth middleware
# creates a new auth_user, they will get admin privs.
# TP (4 Aug 2017): can't find where these are used anywhere in the code.
# But I'll leave them in for now (may want to ask Scott K. about it)
ADMIN_GROUP_HEADER = None
ADMIN_GROUP = None

# Basic auth passwords for LVEM scripted access expire after 365 days.
PASSWORD_EXPIRATION_TIME = timedelta(days=365)

# IP addresses of IFO control rooms
# Used to display signoff pages for operators
# TP (10 Apr 2017): Virgo IP received from Florent Robinet, Franco Carbognani, 
# and Sarah Antier. Corresponds to ctrl1.virgo.infn.it.
CONTROL_ROOM_IPS = {
    'H1': '198.129.208.178',
    'L1': '208.69.128.41',
    'V1': '90.147.136.220',
}

# Everything below here is logging --------------------------------------------

# Base logging settings
LOG_FILE_SIZE = 1024*1024 # 1 MB
LOG_FILE_BAK_CT = 10
LOG_FORMAT = 'extra_verbose'
LOG_LEVEL = 'DEBUG'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

# Note that mode for log files is 'a' (append) by default
# The 'level' specifier on the handle is optional, and we
# don't need it since we're using custom filters.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s | %(message)s',
            'datefmt': LOG_DATEFMT,
        },
        'verbose': {
            'format': '%(asctime)s | %(name)s | %(message)s',
            'datefmt': LOG_DATEFMT,
        },
        'extra_verbose': {
            'format': '%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | ' \
                      + '%(filename)s, line %(lineno)s | %(message)s',
            'datefmt': LOG_DATEFMT,
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'debug_file': {
            'class': 'logging.handlers.ConcurrentRotatingFileHandler',
            'formatter': LOG_FORMAT,
            'filename': join(GRACEDB_PATHS["logs"], "gracedb_debug.log"),
            'maxBytes': (20*1024*1024),
            'backupCount': LOG_FILE_BAK_CT,
            'level': 'DEBUG',
        },
        'error_file': {
            'class': 'logging.handlers.ConcurrentRotatingFileHandler',
            'formatter': LOG_FORMAT,
            'filename': join(GRACEDB_PATHS["logs"], "gracedb_error.log"),
            'maxBytes': LOG_FILE_SIZE,
            'backupCount': LOG_FILE_BAK_CT,
            'level': 'ERROR',
        },
        'performance_file': {
            'class': 'logging.handlers.ConcurrentRotatingFileHandler',
            'maxBytes': 1024*1024,
            'backupCount': 1,
            'formatter': 'simple',
            'filename': join(GRACEDB_PATHS["logs"], "gracedb_performance.log"),
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
        'core': {
            'handlers': ['debug_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'events': {
            'handlers': ['debug_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'performance': {
            'handlers': ['performance_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'ligoauth': {
            'handlers': ['debug_file','error_file'],
            'propagate': True,
            'level': LOG_LEVEL,
        },
        'userprofile': {
            'handlers': ['debug_file','error_file'],
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
