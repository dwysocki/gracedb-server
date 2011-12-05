import os
import sys

# XXX The WSGI files should be unified.
# Would be easy if settings.py were unified, which isn't hard.

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings_dev'

sys.path.append('/home/bmoe/sandbox/lib/python2.6/site-packages')
sys.path.append('/home/bmoe/sandbox/lib/python2.6')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()


