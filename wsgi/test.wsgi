import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Add the source code directory 
sys.path.insert(1,'/home/gracedb/gracedb')

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/gracedb/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

os.environ['MPLCONFIGDIR']='/home/gracedb/logs/'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

