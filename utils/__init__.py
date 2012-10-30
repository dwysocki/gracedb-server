
# GPS time conversion

# This is kind of awful in that leapSeconds
# are hard coded and needs to be kept up to date.
# Also, this probably is/will be/should be in glue.
# Also, there are almost certainly failing edge cases at leap second adjustment times.
# Oh yea, and I don't think this works exactly right for some periods 2006-2008, say.

import pytz
import datetime

import calendar
from time import mktime

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
    (2012, 7, 0, 0, 0, 0, 0, 0, 0),
])

def gpsToPosixTime(gpsTime):
    t = gpsEpoch + gpsTime
    for leap in leapSeconds:
        if t >= leap:
            t = t - 1
    return t

def posixToGpsTime(posixTime):
    change = 0
    for leap in leapSeconds:
        if posixTime > leap:
            change += 1
    return posixTime + change - gpsEpoch

def gpsToUtc(gpsTime):
    t = gpsToPosixTime(gpsTime)
    return datetime.datetime.fromtimestamp(t, pytz.utc)

def isoToGps(t):
    # The input is a string in ISO time format: 2012-10-28T05:04:31.91
    # First strip out whitespace, then split off the factional 
    # second.  We'll add that back later.
    t=t.strip()
    ISOTime = t.split('.')[0]
    ISOTime = datetime.datetime.strptime(ISOTime,"%Y-%m-%dT%H:%M:%S")
    sec_substr = t.split('.')[1]
    if sec_substr:
        fracSec = float('0.' + sec_substr)
    else:
        fracSec = 0
    posixTime = mktime(ISOTime.timetuple()) + fracSec 
    return int(round(posixToGpsTime(posixTime)))
