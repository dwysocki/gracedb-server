import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Sandbox libs here, if required.
#

#sys.path.append('/home/lars/wsgi-sandbox/lib/python2.6')
#sys.path.append('/home/lars/wsgi-sandbox/lib/python2.6/site-packages')
#sys.path.append('/home/gracedb/graceproj')

sys.path.append('/home/branson/sandbox/lib/python2.6/site-packages')
sys.path.append('/home/bmoe/sandbox/lib/python2.6')
sys.path.append('/home/bmoe/sandbox/lib/python2.6/site-packages')
sys.path.append('/home/branson/gracedbdev')

# Scott's Shib app uses loggers.
import logging
logging.basicConfig()

#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s %(levelname)s %(message)s',
#                    filename='/tmp/myapp.log',
#                    filemode='w')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

