import os
import sys

# XXX The WSGI files should be unified.
# Would be easy if settings.py were unified, which isn't hard.

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

