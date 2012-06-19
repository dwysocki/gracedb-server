
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
ROOT_PATH = os.path.abspath( os.path.join( os.path.dirname(__file__), os.pardir ) )

configs = {
    '/home/bmoe/ER2': 'development_er2',
    '/home/bmoe/er2box/lib/python2.6/site-packages/gracedb' : 'development_er2',

    '/home/bmoe/er2box/lib/python2.6/site-packages/ER2' : 'development_er2',

    '/home/bmoe/gracedb': 'development',
    '/home/bmoe/gracedb/gracedb': 'development',

    '/home/gracedb/gracedb': 'production',
    '/home/gracedb/graceproj': 'production',
}


from default import *

config = configs.get(ROOT_PATH, "production")

settings_module = __import__('%s' % config, globals(), locals(), 'gracedb')

# Load the config settings properties into the local scope.
for setting in dir(settings_module):
    if setting == setting.upper():
        locals()[setting] = getattr(settings_module, setting)


