# Django settings for gracedb project.

try:
    # Workaround for a bug
    # http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=473584
    # http://bugs.python.org/setuptools/issue36
    # import MySQLdb followed by import pkg_resources complains
    #   /usr/lib/python2.6/dist-packages/pytz/__init__.py:32: UserWarning: Module _mysql was already imported from /usr/lib/pymodules/python2.6/_mysql.so, but /usr/lib/pymodules/python2.6 is being added to sys.path
    import pkg_resources
except:
    pass


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Brian Moe', 'bmoe@gravity.phys.uwm.edu'),
)

MANAGERS = ADMINS

ALERT_EMAIL_FROM = "Dev Alert <root@moe.phys.uwm.edu>"
ALERT_EMAIL_TO = [
    "Brian Moe <bmoe@gravity.phys.uwm.edu>",
    ]
ALERT_EMAIL_BCC = ["bmoe@uwm.edu"]

ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@moe.phys.uwm.edu>"
ALERT_TEST_EMAIL_TO = [
    "Brian Moe <bmoe@gravity.phys.uwm.edu>",
    ]

# Don't sent out non-test XMPP alerts on dev box!
XMPP_ALERT_CHANNELS = [
                        'test_omega',
                        'test_mbtaonline',
                        'test_cwb',
                        'test_lowmass',
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

SKYALERT_IVORN_PATTERN = "ivo://ligo.org/gracedb#%s-dev"
SKYALERT_ROLE          = "test"
SKYALERT_DESCRIPTION   = "LIGO / Virgo trigger"
SKYALERT_SUBMITTERS = ['Patrick Brady', 'Brian Moe']


# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/bmoe/django/data/latency"
LATENCY_MAXIMUM_CHARTED = 1800
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

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

SITE_ID = 3

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

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
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "gracedb.middleware.auth.LigoAuthContext",
)

AUTHENTICATION_BACKENDS = ('gracedb.middleware.auth.LigoAuthBackend',)

MIDDLEWARE_CLASSES = (
    'gracedb.middleware.accept.AcceptMiddleware',
    'gracedb.middleware.auth.LigoAuthMiddleware',
    'gracedb.middleware.cli.CliExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'gracedb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/bmoe/gracedb/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'gracedb.gracedb',
    'gracedb.userprofile',
)
