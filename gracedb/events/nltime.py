#!/usr/bin/python

# Taken from
# https://web.archive.org/web/20091228182232/http://pyparsing.wikispaces.com/UnderDevelopment

from datetime import datetime, timedelta
from pyparsing import *
from pyparsing import __version__ as pyparsing_version
import calendar
from django.utils import timezone
import pytz

# Note, since the 'now' comes from django.utils.timezone, it will be in UTC.
# We should therefore localize all of the datetime objects generated here to 
# UTC.
 
# string conversion parse actions
def convertToTimedelta(toks):
    unit = toks.timeunit.lower().rstrip("s")
    td = {
        'month'  : timedelta(30),
        'week'    : timedelta(7),
        'day'    : timedelta(1),
        'hour'   : timedelta(0,0,0,0,0,1),
        'minute' : timedelta(0,0,0,0,1),
        'second' : timedelta(0,1),
        }[unit]

    # Backwards compatibility with pyparsing <=2.3.0,
    # feel free to delete once upgrade to 3.0 is complete
    if pyparsing_version <= '2.3.0':
        if toks.qty:
            td *= int(toks.qty)
        if toks.dir:
            td *= toks.dir
    else:
        if toks.qty:
            td *= int(toks.qty[0])
        if toks.dir:
            td *= toks.dir[0]
    toks["timeOffset"] = td
 
def convertToDay(toks):
    now = timezone.now()
    if "wkdayRef" in toks:
        todaynum = now.weekday()
        daynames = [n.lower() for n in calendar.day_name]
        nameddaynum = daynames.index(toks.wkdayRef.day.lower())
        if toks.wkdayRef.dir > 0:
            daydiff = (nameddaynum + 7 - todaynum) % 7
        else:
            daydiff = -((todaynum + 7 - nameddaynum) % 7)
        toks["absTime"] = pytz.utc.localize(datetime(now.year, now.month, now.day)+timedelta(daydiff))
    else:
        name = toks.name.lower()
        toks["absTime"] = {
            "now"       : now,
            "today"     : pytz.utc.localize(datetime(now.year, now.month, now.day)),
            "yesterday" : pytz.utc.localize(datetime(now.year, now.month, now.day)+timedelta(-1)),
            "tomorrow"  : pytz.utc.localize(datetime(now.year, now.month, now.day)+timedelta(+1)),
            }[name]
 
def convertToAbsTime(toks):
    now = timezone.now()
    if "dayRef" in toks:
        day = toks.dayRef.absTime
        day = pytz.utc.localize(datetime(day.year, day.month, day.day))
    else:
        day = pytz.utc.localize(datetime(now.year, now.month, now.day))
    if "timeOfDay" in toks:
        # Backwards compatibility with pyparsing <=2.3.0,
        # feel free to delete once upgrade to 3.0 is complete
        if pyparsing_version <= '2.3.0':
            timeOfDayStr = toks.timeOfDay
        else:
            timeOfDayStr = toks.timeOfDay[0]

        timeOfDay = {
            "now"      : timedelta(0, (now.hour*60+now.minute)*60+now.second, now.microsecond),
            "noon"     : timedelta(0,0,0,0,0,12),
            "midnight" : timedelta(),
        }[timeOfDayStr]
    else:
        timeOfDay = timedelta(0, (now.hour*60+now.minute)*60+now.second, now.microsecond)
    toks["absTime"] = day + timeOfDay
 
def calculateTime(toks):
    if toks.absTime:
        absTime = toks.absTime
    else:
        absTime = timezone.now()
    if toks.timeOffset:
        absTime += toks.timeOffset
    toks["calculatedTime"] = absTime
 
# grammar definitions
CL = CaselessLiteral
today, tomorrow, yesterday, noon, midnight, now = list(map( CL,
    "today tomorrow yesterday noon midnight now".split()))
plural = lambda s : Combine(CL(s) + Optional(CL("s")))
month, week, day, hour, minute, second = list(map(plural,
    "month week day hour minute second".split()))
am = CL("am")
pm = CL("pm")
COLON = Suppress(':')
 
# are these actually operators?
in_ = CL("in").setParseAction(replaceWith(1))
from_ = CL("from").setParseAction(replaceWith(1))
before = CL("before").setParseAction(replaceWith(-1))
after = CL("after").setParseAction(replaceWith(1))
ago = CL("ago").setParseAction(replaceWith(-1))
next_ = CL("next").setParseAction(replaceWith(1))
last_ = CL("last").setParseAction(replaceWith(-1))
 
couple = (Optional(CL("a")) + CL("couple") + Optional(CL("of"))).setParseAction(replaceWith(2))
a_qty = CL("a").setParseAction(replaceWith(1))
integer = Word(nums).setParseAction(lambda t:int(t[0]))
int4 = Group(Word(nums,exact=4).setParseAction(lambda t: [int(t[0][:2]),int(t[0][2:])] ))
qty = integer | couple | a_qty
dayName = oneOf( list(calendar.day_name) )
 
dayOffset = (qty("qty") + (month | week | day)("timeunit"))
dayFwdBack = (from_ + now.suppress() | ago)("dir")
weekdayRef = (Optional(next_ | last_,1)("dir") + dayName("day"))
dayRef = Optional( (dayOffset + (before | after | from_)("dir") ).setParseAction(convertToTimedelta) ) + \
            ((yesterday | today | tomorrow)("name")|
             weekdayRef("wkdayRef")).setParseAction(convertToDay)
todayRef = (dayOffset + dayFwdBack).setParseAction(convertToTimedelta) | \
            (in_("dir") + qty("qty") + day("timeunit")).setParseAction(convertToTimedelta)
 
dayTimeSpec = dayRef | todayRef
dayTimeSpec.setParseAction(calculateTime)
 
hourMinuteOrSecond = (hour | minute | second)
 
timespec = Group(int4("miltime") |
                 integer("HH") + 
                 Optional(COLON + integer("MM")) + 
                 Optional(COLON + integer("SS")) + (am | pm)("ampm")
                 )
absTimeSpec = ((noon | midnight | now | timespec("timeparts"))("timeOfDay") + 
                Optional(dayRef)("dayRef"))
absTimeSpec.setParseAction(convertToAbsTime,calculateTime)
 
relTimeSpec = qty("qty") + hourMinuteOrSecond("timeunit") + \
                (from_ | before | after)("dir") + \
                absTimeSpec("absTime") | \
              qty("qty") + hourMinuteOrSecond("timeunit") + ago("dir") | \
              in_ + qty("qty") + hourMinuteOrSecond("timeunit")
relTimeSpec.setParseAction(convertToTimedelta,calculateTime)
 
nlTimeExpression = (absTimeSpec | dayTimeSpec | relTimeSpec)
 
if __name__ == "__main__":
    # test grammar
    tests = """\
    today
    tomorrow
    yesterday
    in a couple of days
    a couple of days from now
    a couple of days from today
    in a day
    3 days ago
    3 days from now
    a day ago
    now
    10 minutes ago
    10 minutes from now
    in 10 minutes
    in a minute
    in a couple of minutes
    20 seconds ago
    in 30 seconds
    20 seconds before noon
    20 seconds before noon tomorrow
    noon
    midnight
    noon tomorrow
    6am tomorrow
    0800 yesterday
    12:15 AM today
    3pm 2 days from today
    a week from today
    a week from now
    3 weeks ago
    noon next Sunday
    noon Sunday
    noon last Sunday
    2009/12/22 12:13:14""".splitlines()
     
    for t in tests:
        print(t, "(relative to %s)" % timezone.now())
        res = nlTimeExpression.parseString(t)
        if "calculatedTime" in res:
            print(res.calculatedTime)
        else:
            print("???")
        print()
     
