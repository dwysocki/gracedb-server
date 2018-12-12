from datetime import timedelta, datetime
from dateutil import parser
import json
import pytz

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from events.models import Event, Pipeline, Search, Group

# Default settings
LOOKBACK_HOURS = 720
BIN_WIDTH = 24

# Set up time range
end_time = datetime.utcnow()
end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
end_time = pytz.utc.localize(end_time)
start_time = end_time - timedelta(hours=LOOKBACK_HOURS)
# Convert to ISOformat
start_time = start_time.isoformat()
end_time = end_time.isoformat()

# get_counts_for_bin
# Takes as input:
# - the lower bin boundary (a naive datetime object in UTC)
# - the bin_width in hours
# - the pipeline we are interested in
# Returns the number of events in that bin, excluding MDC and Test.
MDC = Search.objects.get(name='MDC')
Test = Group.objects.get(name='Test')

# make a list of pipeline objects
PIPELINES = []
for n in settings.BINNED_COUNT_PIPELINES:
    try:
        PIPELINES.append(Pipeline.objects.get(name=n))
    except:
        pass
OTHER_PIPELINES = []
for p in Pipeline.objects.all():
    if p.name not in PIPELINES:
        OTHER_PIPELINES.append(p)


def get_counts_for_bin(lbb, bin_width, pipeline):
    ubb = lbb + timedelta(hours=bin_width)
    events = Event.objects.filter(pipeline=pipeline, created__range=(lbb, ubb))
    if MDC:
        events = events.exclude(search=MDC)
    if Test:
        events = events.exclude(group=Test)
    return events.count()


# given a date string, parse it and localize to UTC if necessary
def parse_and_localize(date_string):
    if not date_string:
        return None
    dt = parser.parse(date_string)
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    return dt


def get_record(lbb, bin_width):
    bc = lbb + timedelta(hours=bin_width/2)
    r = { 'time': bc, 'delta_t': bin_width }
    total = 0
    for p in PIPELINES:
        count = get_counts_for_bin(lbb, bin_width, p)
        total += count
        r[p.name] = count
    other = 0
    for p in OTHER_PIPELINES:
        other += get_counts_for_bin(lbb, bin_width, p)
    r['Other'] = other
    total += other
    r['Total'] = total
    return r


def dt_record(r):
    r['time'] = parse_and_localize(r['time'])
    return r


def strtime_record(r):
    r['time'] = r['time'].replace(tzinfo=None).isoformat()
    return r


class Command(BaseCommand):
    help = 'Manage the binned counts file used for plotting rates.'

    def handle(self, *args, **options):
        # First of all, that bin width had better be an even number of hours.
        bin_width = BIN_WIDTH
        if bin_width % 2 != 0:
            raise ValueError("Bin width must be divisible by 2. Sorry.")

        # Let's take our desired range and turn it into UTC datetime objects
        start = parse_and_localize(start_time)
        end = parse_and_localize(end_time)

        duration = end - start
        # This timedelta has days, seconds, and total seconds.
        # What we want to verify is that that is an integer number of hours.
        # That is, the total seconds should be divisible by 3600.
        hours, r_seconds = divmod(duration.total_seconds(), 3600)
        if r_seconds != 0.0:
            msg = "The start and end times must be separated by an integer number of hours."
            raise ValueError(msg)

        # Now we need to verify that the number of hours is divisible by our
        # bin width
        bins, r_hours = divmod(hours, bin_width)
        bins = int(bins)

        if r_hours != 0.0:
            msg = "The start and end times must correspond to an integer number of bins."
            raise ValueError(msg)

        # read in the file and interpret it as JSON
        f = None
        try:
            f = open(settings.BINNED_COUNT_FILE, 'r')
        except:
            pass

        records = []
        if f:
            try:
                records = json.loads(f.read())
            except:
                pass
            f.close()

        # process the records so that the time is a datetime for all of them
        # Note that the times here are at the bin centers
        records = [dt_record(r) for r in records]

        # accumlate the necessary records
        new_records = []
        for i in range(bins):
            lbb = start + timedelta(hours = i*bin_width)
            bc = lbb + timedelta(hours = bin_width/2)
            # look for an existing record with the desired lower bin
            # boundary and delta.
            found = False
            for r in records:
                if bc == r['time'] and bin_width == r['delta_t']:
                    found = True
                    new_records.append(r)
            if not found:
                new_records.append(get_record(lbb, bin_width))

        new_records = [strtime_record(r) for r in new_records]

        # write out the file
        f = open(settings.BINNED_COUNT_FILE, 'w')
        f.write(json.dumps(new_records))
        f.close()
