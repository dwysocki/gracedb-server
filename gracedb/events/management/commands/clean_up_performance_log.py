import datetime
import re

from django.conf import settings
from django.core.management.base import BaseCommand

# Parameters
LOOKBACK_TIME = 5 # days
LOG_FILE_PATH = settings.LOGGING['handlers']['performance_file']['filename']


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        # Read log
        logfile = open(LOG_FILE_PATH, "r")
        lines = logfile.readlines()
        logfile.close()

        # Lookback time is 5 days.
        dt_now = datetime.datetime.now()
        dt_min = dt_now + datetime.timedelta(days=-1*LOOKBACK_TIME)

        # Get "fresh" enough log messages from logfile
        dateformat = settings.LOG_DATEFMT
        logfile_str = ""
        for line in lines:

            # Check the date to see whether it's fresh enough
            match = re.search(r'^(.*) \| .*', line)
            datestring = match.group(1)
            dt = datetime.datetime.strptime(datestring, dateformat)
            if dt > dt_min:
                logfile_str += line

        # Overwrite file
        logfile = open(LOG_FILE_PATH, "w")
        logfile.write(logfile_str)
        logfile.close()
