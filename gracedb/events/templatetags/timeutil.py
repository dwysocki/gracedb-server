
from django import template
from django.conf import settings
from django.utils import dateformat

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from core.time_utils import posixToGpsTime, gpsToUtc

import pytz
import time
import datetime
import decimal

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

def get_multitime_value(t, label, autoescape, format):
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
        # XXX in order for mktime to give correct results, the time must be
        # in the server's timezone.
        dt = dt.astimezone(SERVER_TZ)
        posix_time = time.mktime(dt.timetuple())
        gps_time = int(posixToGpsTime(posix_time))
    elif isinstance(t, int):
        gps_time = t
        dt = gpsToUtc(t)
        # Note: must convert to server timezone before calling mktime
        posix_time = time.mktime(dt.astimezone(SERVER_TZ).timetuple())
    elif isinstance(t, decimal.Decimal):
        gps_time = round(float(t),3)
        dt = gpsToUtc(t)
        posix_time = time.mktime(dt.astimezone(SERVER_TZ).timetuple())
    else:
        return "N/A"
        return '<time utc="%s" gps="%s" llo="%s" lho="%s" virgo="%s" jsparsable="%s"%s>%s</time>' % \
            8*("N/A",)
        # raise ValueError("time must be type int or datetime, not '%s'" % type(t))

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

    rv = '<time utc="%s" gps="%14.3f" llo="%s" lho="%s" virgo="%s" jsparsable="%s"%s>%s</time>' % \
            (utc_time, gps_time, llo_time, lho_time, virgo_time, js_parsable_time, label_attr, display_time)

    return mark_safe(rv)

@register.filter
def multiTime(t, label, autoescape=None):
    format = FORMAT
    return get_multitime_value(t, label, autoescape, format)
multiTime.needs_autoescape = True

@register.filter
def multiTimeMicroSeconds(t, label, autoescape=None):
    format = 'Y-m-d H:i:s.u T'
    return get_multitime_value(t, label, autoescape, format)
multiTimeMicroSeconds.needs_autoescape = True

@register.filter
def timeselect(label, default, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x


    rv = """"""
    rv += """<select class="form-control form-control-sm form-control-picker"
          """
    rv += """id="{}" onChange="changeTime(this, '{}')">""".format(esc(label),esc(label))
    rv += """<option value="" disabled selected>{}</option>""".format(ts_label(label))
    rv += """<option data-divider="true"></option>"""

    for value, displayname in [
            ("gps", "GPS Time"),
            ("llo", "LLO Local"),
            ("lho", "LHO Local"),
            ("virgo", "Virgo Local"),
            ("utc", "UTC"),]:
        rv += '<option value="{}">{}</option>'.format(esc(value), esc(displayname))
    rv += """</select>"""


    return mark_safe(rv)
timeselect.needs_autoescape = True

# Makes a nice looking label for display 
# out of the 'label' used for a time select.
def ts_label(label):
    label_choices = {'gps': 'Event Time',
                     'ngps': 'Event Time',
                     'created': 'Created',
                     'submitted': 'Submitted',
                     'nsubmitted': 'Submitted',
                     'lcreated': 'Log Entry Created'}
    return label_choices[label]

@register.filter(name='utc')
def utc(dt, format=FORMAT):
    if not dt.tzinfo:
        dt = SERVER_TZ.localize(dt)
    dt = dt.astimezone(pytz.utc)
    return dateformat.format(dt, format)


@register.filter
def gpsdate(gpstime, format=FORMAT):
    return dateformat.format(gpsToUtc(gpstime), format)

@register.filter
def gpsdate_tz(gpstime, label="utc"):
    format = FORMAT
    dt = gpsToUtc(gpstime)
    if label=='lho':
        dt = dt.astimezone(LHO_TZ)
    elif label=='llo':
        dt = dt.astimezone(LLO_TZ)
    elif label=='virgo':
        dt = dt.astimezone(VIRGO_TZ)
    return dateformat.format(dt, format)

@register.filter
def gpstime(dt):
    if not dt.tzinfo:
        dt = SERVER_TZ.localize(dt)
    # convert to SERVER_TZ if not already
    dt = dt.astimezone(SERVER_TZ)
    posix_time = time.mktime(dt.timetuple())
    gps_time = int(posixToGpsTime(posix_time))
    return gps_time

def timeSelections(t):
    rv = {}
    if t is None:
        return rv
    format = FORMAT
    if isinstance(t, datetime.datetime):
        dt = t
        if not dt.tzinfo:
            dt = SERVER_TZ.localize(dt)
        dt = dt.astimezone(SERVER_TZ)
        posix_time = time.mktime(dt.timetuple())
        gps_time = int(posixToGpsTime(posix_time))
    elif isinstance(t, int):
        gps_time = t
        dt = gpsToUtc(t)
        posix_time = time.mktime(dt.astimezone(SERVER_TZ).timetuple())
    elif isinstance(t, decimal.Decimal):
        gps_time = float(t)
        dt = gpsToUtc(t)
        posix_time = time.mktime(dt.astimezone(SERVER_TZ).timetuple())
    else:
        raise ValueError("time must be type int or datetime, not '%s'" % type(t))

    # JavaScript -- parsable by Date() object constructor
    # "Jan 2, 1985 00:00:00 UTC"
    #js_parsable_time = dateformat.format(dt, "F j, Y h:i:s")+" UTC"

    rv['gps'] = gps_time
    rv['lho'] = dateformat.format(dt.astimezone(LHO_TZ), format)
    rv['llo'] = dateformat.format(dt.astimezone(LLO_TZ), format)
    rv['virgo'] = dateformat.format(dt.astimezone(VIRGO_TZ), format)
    rv['utc'] = dateformat.format(dt.astimezone(pytz.utc), format)

    return rv

# XXX Branson added this. God will punish me.
@register.filter
def end_time(event,digits=4):
    try:
        #return float(event.end_time) + float(event.end_time_ns)/1.e9
        # The approach above did not work. For some reason, the value loses precision
        # in the django template, so that the final digits get truncated and padded 
        # with zeros. Why? The current gpstime is only 10 digits. So I'm going to have to
        # make this into a string. Totally sick, I know.
        decimal_part = round(float(event.end_time_ns)/1.e9,digits)
        # ugh. must pad with zeros to the right.
        decimal_part = str(decimal_part)[1:].ljust(digits+1,'0')
        return str(event.end_time) + decimal_part
    except Exception:
        return None

