import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Add the source code directory 
sys.path.insert(1,'/home/branson/gracedbdev')

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/branson/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

os.environ['MPLCONFIGDIR']='/home/branson/logs/'

#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

