
# Django settings for gracedb project.

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
ROOT_PATH = os.path.abspath( os.path.join( os.path.dirname(__file__), os.pardir ) )

configs = {
    '/home/gracedb/gracedb': 'production',
    '/home/gracedb/graceproj': 'production',

    '/home/roywilliams/gracedbdev': 'roy',
    '/home/roywilliams/gracedbdev/gracedb': 'roy',
}

from default import *

config = configs.get(ROOT_PATH, "production")

# If host is NOT gracedb, use test settings.
hostname = socket.gethostname()
if (hostname != 'gracedb'):
    config = 'test'

settings_module = __import__('%s' % config, globals(), locals(), 'gracedb')

# Load the config settings properties into the local scope.
for setting in dir(settings_module):
    if setting == setting.upper():
        locals()[setting] = getattr(settings_module, setting)


