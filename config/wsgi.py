import os
import sys
from os.path import abspath, dirname, join

# Parameters
DEFAULT_SETTINGS_MODULE = 'config.settings.vm.dev'
PROJECT_ROOT_NAME = 'gracedb'

# Set up base dir of repository
BASE_DIR = abspath(join(dirname(__file__), ".."))

# Add the source code directory and project root
sys.path.append(BASE_DIR)
sys.path.append(join(BASE_DIR, PROJECT_ROOT_NAME))

# Set DJANGO_SETTINGS_MODULE environment variable if it's not already set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', DEFAULT_SETTINGS_MODULE)

# Matplotlib config directory
os.environ['MPLCONFIGDIR'] = '/tmp/'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
