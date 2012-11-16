
# Suitable for production

DEBUG = False
TEMPLATE_DEBUG = DEBUG

EMAIL_HOST = 'gravity.phys.uwm.edu'

ADMINS = (
    ('Brian Moe', 'bmoe@gravity.phys.uwm.edu'),
)

MANAGERS = ADMINS

ALERT_EMAIL_FROM = "GraCEDb <gracedb@archie.phys.uwm.edu>"
ALERT_EMAIL_TO = [
#                 "gracedb@listserv.ligo.org",
                 ]
ALERT_EMAIL_BCC = [
                  ]

ALERT_TEST_EMAIL_FROM = "GraCEDb TEST <gracedb@archie.phys.uwm.edu>"
ALERT_TEST_EMAIL_TO = [
                      ]

XMPP_ALERT_CHANNELS = [
                        'burst_omega',
                        'test_omega',
                        'cbc_mbtaonline',
                        'test_mbtaonline',
                        'burst_cwb',
                        'test_cwb',
                        'cbc_lowmass',
                        'test_lowmass',
                        'cbc_highmass',
                        'test_highmass',
                        'test_grb',
                      ]

DATABASES = {
    'default' : {
        'NAME'     : 'gracedb',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'gracedb',
        'PASSWORD' : 'redrum4x',
    }
}

# SkyAlert

SKYALERT_IVORN_PATTERN = "ivo://ligo.org/gracedb#%s"
SKYALERT_ROLE          = "test"
SKYALERT_DESCRIPTION   = "LIGO / Virgo trigger"
SKYALERT_SUBMITTERS = ['Patrick Brady', 'Brian Moe']


GRACEDB_DATA_DIR = "/mnt/gracedb-web/data"
#GRACEDB_DATA_DIR = "/mnt/gracedb-web-temp/data"
#GRACEDB_DATA_DIR = "/home/branson/fake_data"

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/gracedb/data/latency"
LATENCY_MAXIMUM_CHARTED = 1800
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/home/gracedb/data/uptime"


# Find another way to do this.
#
# CBC IFAR Reports

from utils import posixToGpsTime
from datetime import datetime, timedelta
import time

now = datetime.now()
yesterday = now - timedelta(days=1)
lastweek = now - timedelta(days=7)
now = posixToGpsTime(time.mktime(now.timetuple()))
yesterday = posixToGpsTime(time.mktime(yesterday.timetuple()))
lastweek = posixToGpsTime(time.mktime(lastweek.timetuple()))

REPORT_IFAR_IMAGE_DIR = LATENCY_REPORT_DEST_DIR
REPORTS_IFAR = [
    #(query, axis_label, title, fname),
    ("LowMass %d..%d" % (yesterday, now),
     "GraceDB CBC LowMass ER1 events",
     "ER1 FARs from gstlal_ll_inspiral - last day",
     "ifar_day.png"
    ),
    ("LowMass %d..%d" % (lastweek, now),
     "GraceDB CBC LowMass ER1 events",
     "ER1 FARs from gstlal_ll_inspiral - last week",
     "ifar_week.png"
    ),
]


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

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/gracedb-static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$$&hl%^_4&s0k7sbdr8ll_^gkz-j8oab0tz$t^^b-%$!83d(av'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    #'django.template.loaders.filesystem.load_template_source',
    # replaced by...
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
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

AUTHENTICATION_BACKENDS = (
    'gracedb.middleware.auth.LigoAuthBackend',
    'ligodjangoauth.LigoShibbolethAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SHIB_AUTHENTICATION_SESSION_INITIATOR = 'https://moe.phys.uwm.edu/Shibboleth.sso/Login'

MIDDLEWARE_CLASSES = [
    'middleware.accept.AcceptMiddleware',
    'middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'ligodjangoauth.LigoShibbolethMiddleware',
    'gracedb.middleware.auth.LigoAuthMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/gracedb/graceproj/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'gracedb',
    'userprofile',
    'rest_framework',
)

REST_FRAMEWORK = {
    'PAGINATE_BY': 10
}


STATIC_URL = "/gracedb-static/"

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_DIRS = ()
