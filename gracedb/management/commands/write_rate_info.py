from django.conf import settings
from django.core.management.base import NoArgsCommand
from gracedb.reports import rate_data
import json

class Command(NoArgsCommand):
    help = "I write down rate data in JSON to disk. That's about it."

    def handle_noargs(self, **options):
        outfile = open(settings.RATE_INFO_FILE, 'w')
        json_data = json.dumps(rate_data())
        outfile.write(json_data)
        outfile.close()
