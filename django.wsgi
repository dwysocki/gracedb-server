import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Sandbox libs here, if required.
#

sys.path.append('/home/lars/wsgi-sandbox/lib/python2.6')
sys.path.append('/home/lars/wsgi-sandbox/lib/python2.6/site-packages')
sys.path.append('/home/gracedb/gracedb')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

