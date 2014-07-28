import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Sandbox libs here, if required.
#

sys.path.insert(1,'/home/branson/gracedbdev')
sys.path.insert(1,'/home/branson/djangoenv/lib/python2.7/site-packages')

# Scott's Shib app uses loggers.
import logging
logging.basicConfig()

os.environ['MPLCONFIGDIR']='/home/branson/logs/'

#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s %(levelname)s %(message)s',
#                    filename='/tmp/myapp.log',
#                    filemode='w')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

