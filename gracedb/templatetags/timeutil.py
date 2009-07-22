
from django import template
from django.conf import settings
from django.utils import dateformat

import pytz

# DATETIME_SETTINGS is guaranteed to be set.  GRACE_DATETIME_FORMAT is not.
FORMAT = getattr(settings, 'GRACE_DATETIME_FORMAT', settings.DATETIME_FORMAT)

LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)

register = template.Library()

@register.filter(name='utc')
def utc(dt, format=FORMAT):
    if not dt.tzinfo:
        dt = LOCAL_TZ.localize(dt)
    dt = dt.astimezone(pytz.utc)
    return dateformat.format(dt, format)

@register.filter(name='gpsdate')
def gpsdate(gpstime, format=FORMAT):
    return dateformat.format(gpsToUTC(gpstime), format)



# GPS time conversion

# This is kind of awful in that leapSeconds
# are hard coded and needs to be kept up to date.
# Also, this should be somewhere else.

import calendar, datetime

gpsEpoch = calendar.timegm((1980, 1, 6, 0,  0,  0,  0,  0,  0))

leapSeconds = map(calendar.timegm, [
    (1981, 7, 0, 0, 0, 0, 0, 0, 0),
    (1982, 7, 0, 0, 0, 0, 0, 0, 0),
    (1983, 7, 0, 0, 0, 0, 0, 0, 0),
    (1985, 7, 0, 0, 0, 0, 0, 0, 0),
    (1988, 1, 0, 0, 0, 0, 0, 0, 0),
    (1990, 1, 0, 0, 0, 0, 0, 0, 0),
    (1991, 1, 0, 0, 0, 0, 0, 0, 0),
    (1992, 7, 0, 0, 0, 0, 0, 0, 0),
    (1993, 7, 0, 0, 0, 0, 0, 0, 0),
    (1994, 7, 0, 0, 0, 0, 0, 0, 0),
    (1996, 1, 0, 0, 0, 0, 0, 0, 0),
    (1997, 7, 0, 0, 0, 0, 0, 0, 0),
    (1999, 1, 0, 0, 0, 0, 0, 0, 0),
    (2006, 1, 0, 0, 0, 0, 0, 0, 0),
    (2009, 1, 0, 0, 0, 0, 0, 0, 0),
])

def gpsToPosixTime(gpsTime):
    t = gpsEpoch + gpsTime
    for leap in leapSeconds:
        if t >= leap:
            t = t - 1
    return t

def gpsToUTC(gpsTime):
    t = gpsToPosixTime(gpsTime)
    return datetime.datetime.fromtimestamp(t, pytz.utc)
