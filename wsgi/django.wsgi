import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Add the source code directory
sys.path.append('/home/gracedb/graceproj')

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/gracedb/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

os.environ['MPLCONFIGDIR']='/tmp/'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

