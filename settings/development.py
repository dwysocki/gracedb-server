
CONFIG_NAME = "DEVELOPMENT"

DEBUG = True
TEMPLATE_DEBUG = DEBUG


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
 
# SkyAlert
SKYALERT_IVORN_PATTERN = "ivo://ligo.org/gracedb#%s-dev"

# Latency histograms.  Where they go and max latency to bin.
LATENCY_REPORT_DEST_DIR = "/home/bmoe/data/latency"
LATENCY_REPORT_WEB_PAGE_FILE_PATH = LATENCY_REPORT_DEST_DIR + "/latency.inc"

# Uptime reporting
UPTIME_REPORT_DIR = "/home/bmoe/data/uptime"


SITE_ID = 1

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/home/bmoe/gracedb/templates",
)
