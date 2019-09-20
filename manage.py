#!/usr/bin/env python

import os
from os.path import abspath, dirname, exists, join
import sys

# Parameters
DEFAULT_SETTINGS_MODULE = 'config.settings.vm.dev'
PROJECT_ROOT_NAME = 'gracedb'
BASE_DIR = abspath(dirname(__file__))
VENV_PATH = abspath(join(BASE_DIR, '..', 'djangoenv'))

if __name__ == '__main__':
    # Add the project root to the python path.
    sys.path.append(join(BASE_DIR, PROJECT_ROOT_NAME))

    # Set up virtualenv if it exists and is not active
    if (exists(VENV_PATH) and 'VIRTUAL_ENV' not in os.environ):
        VIRTUALENV_ACTIVATOR = abspath(join(VENV_PATH, 'bin',
            'activate_this.py'))
        exec(
            open(VIRTUALENV_ACTIVATOR).read(),
            {'__file__': VIRTUALENV_ACTIVATOR}
        )

    # Set DJANGO_SETTINGS_MODULE environment variable
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', DEFAULT_SETTINGS_MODULE)

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
