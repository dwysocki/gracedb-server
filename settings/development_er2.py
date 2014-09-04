

CONFIG_NAME = "ER2"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default' : {
        'NAME'     : 'er2',
        'ENGINE'   : 'django.db.backends.mysql',
        'USER'     : 'er2',
        'PASSWORD' : 'weasel',
    }
}

ALERT_EMAIL_FROM = "Dev Alert <root@moe.phys.uwm.edu>"
ALERT_EMAIL_TO = [
    "Brian Moe <bmoe@gravity.phys.uwm.edu>",
    ]
ALERT_EMAIL_BCC = ["bmoe@uwm.edu"]

ALERT_TEST_EMAIL_FROM = "Dev Test Alert <root@moe.phys.uwm.edu>"
ALERT_TEST_EMAIL_TO = [
    "Brian Moe <bmoe@gravity.phys.uwm.edu>",
    ]

XMPP_ALERT_CHANNELS = [
                      ]
 
# SkyAlert
SKYALERT_IVORN_PATTERN = "ivo://ligo.org/gracedb#%s-dev-er2"

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/bmoe/data/latency"

SITE_ID = 4

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/bmoe/ER2/templates",
)


