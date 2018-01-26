import os
import sys
from os.path import abspath, dirname, join

# Parameters
SETTINGS_MODULE = 'config.settings'
PROJECT_ROOT_NAME = 'gracedb'
VENV_NAME = 'djangoenv'

# Set DJANGO_SETTINGS_MODULE environment variable if not already set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', SETTINGS_MODULE)

# Set up base dir of repository
BASE_DIR = abspath(join(dirname(__file__), ".."))

# Add the source code directory and project root
sys.path.append(BASE_DIR)
sys.path.append(join(BASE_DIR, PROJECT_ROOT_NAME))

# Activate the virtual environment
VIRTUALENV_ACTIVATOR = abspath(join(BASE_DIR, '..', VENV_NAME, 'bin',
    'activate_this.py'))
execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

# Matplotlib config directory
os.environ['MPLCONFIGDIR'] = '/tmp/'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

