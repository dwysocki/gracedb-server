import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['MPLCONFIGDIR']='/tmp/'

# Sandbox libs here, if required.
#
#sys.path.append('/home/jkanner/djangoenv/lib/python2.7/site-packages')
#sys.path.append('/home/jkanner/djangoenv/lib/python2.7')
sys.path.append('/home/roywilliams/gracedbdev')
sys.path.append('/home/roywilliams')

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/branson/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

# Scott's Shib app uses loggers.
import logging
logging.basicConfig()

os.environ['MPLCONFIGDIR']='/tmp/'

#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s %(levelname)s %(message)s',
#                    filename='/tmp/myapp.log',
#                    filemode='w')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

