import os
import sys

# XXX The WSGI files should be unified.
# Would be easy if settings.py were unified, which isn't hard.

sys.path.append('/home/lars/django')

# OK, the lib/lib64 situation should be handled better.

sys.path.append('/opt/lscsoft/glue/lib64/python2.4/site-packages')
sys.path.append('/opt/lscsoft/glue/lib/python2.4/site-packages')

sys.path.append('/opt/lscsoft/pylal/lib/python2.4/site-packages')
sys.path.append('/opt/lscsoft/pylal/lib64/python2.4/site-packages')

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

