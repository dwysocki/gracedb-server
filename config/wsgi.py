import os
import sys
from os.path import abspath, dirname, join

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Set up base dir of repository
BASE_DIR = abspath(join(dirname(__file__), ".."))

# Add the source code directory and project root
sys.path.append(BASE_DIR)
sys.path.append(join(BASE_DIR, "apps"))

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = "/home/gracedb/djangoenv/bin/activate_this.py"
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

# Matplotlib config directory
os.environ['MPLCONFIGDIR']='/tmp/'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

