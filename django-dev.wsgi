import os
import sys

sys.path.append('/home/lars/django')

# OK, the lib/lib64 situation should be handled better.

sys.path.append('/opt/lscsoft-bleed/glue/lib64/python2.4/site-packages')
sys.path.append('/opt/lscsoft-bleed/lib/python2.4/site-packages')

sys.path.append('/opt/lscsoft/pylal/lib/python2.4/site-packages')
sys.path.append('/opt/lscsoft/pylal/lib64/python2.4/site-packages')

os.environ['DJANGO_SETTINGS_MODULE'] = 'gracedb.settings_dev'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

#os.environ['PKG_CONFIG_PATH'] = "${HOME}/lib/pkgconfig:${PKG_CONFIG_PATH}"

