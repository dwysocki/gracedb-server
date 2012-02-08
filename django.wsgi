import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings'

# Sandbox libs here, if required.
#
#sys.path.append('/home/bmoe/sandbox/lib/python2.6/site-packages')
#sys.path.append('/home/bmoe/sandbox/lib/python2.6')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

