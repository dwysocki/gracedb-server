import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Add the source code directory
sys.path.append('/home/gracedb/gracedb')

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/gracedb/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

os.environ['MPLCONFIGDIR']='/tmp/'

# Changed for compatibility with django 1.7.8
#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

