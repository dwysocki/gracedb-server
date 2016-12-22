"""
Django settings for gracedb project.

Default settings are in default.py. Custom settings for individual server
instances are stored in separate files (production.py, test.py, etc.)
and are loaded/managed by this file.
"""

try:
    # Workaround for a bug
    # http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=473584
    # http://bugs.python.org/setuptools/issue36
    # import MySQLdb followed by import pkg_resources complains
    #   /usr/lib/python2.6/dist-packages/pytz/__init__.py:32: UserWarning: Module _mysql was already imported from /usr/lib/pymodules/python2.6/_mysql.so, but /usr/lib/pymodules/python2.6 is being added to sys.path
    import pkg_resources
except:
    pass

import os
import socket
from default import * # import default settings

# Get path to this file
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Config dictionary:
#   Key:   path to this file
#   Value: name of custom settings file to load
configs = {
    '/home/gracedb/gracedb': 'production',
    '/home/gracedb/graceproj': 'production',

    '/home/roywilliams/gracedbdev': 'roy',
    '/home/roywilliams/gracedbdev/gracedb': 'roy',
}


# Get custom settings file from configs dict, but
# default to production if key not found.
config = configs.get(ROOT_PATH, "production")

# If host is gracedb-test, use custom test settings.
if socket.gethostname() == 'gracedb-test':
    config = 'test'

# Import custom settings
settings_module = __import__('%s' % config, globals(), locals(), 'gracedb')

# Load the custom config settings properties into the local scope.
for setting in dir(settings_module):
    if setting == setting.upper():
        locals()[setting] = getattr(settings_module, setting)


