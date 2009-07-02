import os
import sys

sys.path.append('/home/lars/django')

sys.path.append('/opt/lscsoft/glue/lib64/python2.4/site-packages')
sys.path.append('/opt/lscsoft/glue/lib/python2.4/site-packages')

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings'
#os.environ['PYTHON_EGG_CACHE'] = '/tmp/egg-trash'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

