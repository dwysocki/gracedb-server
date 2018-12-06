#!/usr/bin/env python

import os
from os.path import abspath, dirname, join
import sys

# Parameters
DEFAULT_SETTINGS_MODULE = 'config.settings.dev'
PROJECT_ROOT_NAME = 'gracedb'
VENV_NAME = 'djangoenv'

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', DEFAULT_SETTINGS_MODULE)

    # Add the project root to the python path.
    BASE_DIR = abspath(dirname(__file__))
    sys.path.append(join(BASE_DIR, PROJECT_ROOT_NAME))

    # Set up virtualenv if not active
    if ('VIRTUAL_ENV' not in os.environ):
        VIRTUALENV_ACTIVATOR = abspath(join(BASE_DIR, '..', VENV_NAME, 'bin',
            'activate_this.py'))
        execfile(VIRTUALENV_ACTIVATOR, dict(__file__=VIRTUALENV_ACTIVATOR))

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
