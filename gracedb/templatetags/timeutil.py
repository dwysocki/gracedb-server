
from django import template
from django.conf import settings
from django.utils import dateformat

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from gracedb.utils import posixToGpsTime, gpsToUtc

import pytz
import time
import datetime

# DATETIME_SETTINGS is guaranteed to be set.  GRACE_DATETIME_FORMAT is not.
FORMAT = getattr(settings, 'GRACE_DATETIME_FORMAT', settings.DATETIME_FORMAT)

SERVER_TZ = pytz.timezone(settings.TIME_ZONE)

LLO_TZ   = pytz.timezone("America/Chicago")
LHO_TZ   = pytz.timezone("America/Los_Angeles")
VIRGO_TZ = pytz.timezone("Europe/Rome")

register = template.Library()

# OK.  What we're trying to do here is,
#   given a time in some time system, gps, posix, datetime, whatever,
#   produce something that will render in a desired manner and will
#   be javascript-convertible to other formats/timezones/what-have-you.
#
#   So... these filters, which are named after their timekeeping system,
#   will convert from that time system, to ...
#     <time value="POSIX TIME VALUE" [label="LABEL"]>FORMATTED TIME</time>

@register.filter
def multiTime(t, label, autoescape=None):
    format = FORMAT

    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    if label is not None:
        label_attr = ' name="time-%s"' % esc(label)
    else:
        label_attr = ""

    if isinstance(t, datetime.datetime):
        dt = t
        if not dt.tzinfo:
            dt = SERVER_TZ.localize(dt)
        #dt = dt.astimezone(pytz.utc)
        posix_time = time.mktime(dt.timetuple())
        gps_time = int(posixToGpsTime(posix_time))
    elif isinstance(t, int) or isinstance(t, long):
        gps_time = t
        dt = gpsToUtc(t)
        posix_time = time.mktime(dt.timetuple())
    else:
        raise ValueError("time must be type int, long or datetime, not '%s'" % type(t))

    # JavaScript -- parsable by Date() object constructor
    # "Jan 2, 1985 00:00:00 UTC"
    js_parsable_time = esc(dateformat.format(dt, "F j, Y h:i:s")+" UTC")

    lho_time = esc(dateformat.format(dt.astimezone(LHO_TZ), format))
    llo_time = esc(dateformat.format(dt.astimezone(LLO_TZ), format))
    virgo_time = esc(dateformat.format(dt.astimezone(VIRGO_TZ), format))
    utc_time = esc(dateformat.format(dt.astimezone(pytz.utc), format))

    if isinstance(t, datetime.datetime):
        display_time = utc_time
    else:
        display_time = gps_time

    rv = '<time utc="%s" gps="%s" llo="%s" lho="%s" virgo="%s" jsparsable="%s"%s>%s</time>' % \
            (utc_time, gps_time, llo_time, lho_time, virgo_time, js_parsable_time, label_attr, display_time)

    return mark_safe(rv)
multiTime.needs_autoescape = True


@register.filter
def timeselect(label, default, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    rv = """<form><select onChange="changeTime(this, '%s')">""" % esc(label)
    for value, displayname in [
            ("gps", "GPS Time"),
            ("llo", "LLO Local"),
            ("lho", "LHO Local"),
            ("virgo", "Virgo Local"),
            ("utc", "UTC"),]:
        selected = ""
        if value == default:
            selected = " SELECTED"
        rv += '<option value="%s"%s>%s</option>' % (esc(value), selected, esc(displayname))
    rv += "</select></form>"
    return mark_safe(rv)
timeselect.needs_autoescape = True


@register.filter(name='utc')
def utc(dt, format=FORMAT):
    if not dt.tzinfo:
        dt = SERVER_TZ.localize(dt)
    dt = dt.astimezone(pytz.utc)
    return dateformat.format(dt, format)


@register.filter
def gpsdate(gpstime, format=FORMAT):
    return dateformat.format(gpsToUtc(gpstime), format)

