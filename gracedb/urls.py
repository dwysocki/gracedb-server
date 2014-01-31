
from django.conf.urls.defaults import *

#import django.views.generic.list_detail

from gracedb.api import download

urlpatterns = patterns('gracedb.views',
    url (r'^$', 'index', name="home"),
    url (r'^create/$', 'create', name="create"),
    url (r'^search/(?P<format>(json|flex))?$', 'search', name="search"),
    url (r'^gstlalcbc_report/(?P<format>(json|flex))?$', 'gstlalcbc_report', name="gstlalcbc_report"),
    url (r'^view/(?P<graceid>[GEHT]\d+)', 'view', name="view"),
    url (r'^voevent/(?P<graceid>[GEHT]\d+)', 'voevent', name="voevent"),
    url (r'^skyalert/(?P<graceid>[GEHT]\d+)', 'skyalert', name="skyalert"),
    url (r'^neighbors/(?P<graceid>[GEHT]\d+)/\(?(?P<delta1>[-+]?\d+)(,(?P<delta2>[-+]?\d+)\)?)?', 'neighbors', name="neighbors"),
    url (r'^(?P<graceid>[GEHT]\d+)$', 'view', name="view2"),
    url (r'^(?P<graceid>[GEHT]\d+)/files/(?P<filename>.*)$', download, name="file"),
    url (r'^(?P<graceid>[GEHT]\d+)/log/(?P<num>([\d]*|preview))$', 'logentry', name="logentry"),
    url (r'^(?P<graceid>[GEHT]\d+)/log/(?P<num>\d+)/tag/(?P<tagname>\w+)$', 'taglogentry', name="taglogentry"),


#   (r'^view/(?P<uid>[\w\d]+)', 'view'),
#   (r'^edit/(?P<uid>[\w\d]+)', 'edit'),
#   (r'^request_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'request_archive'),
#   (r'^approve_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'approve_archive'),
#   url (r'^query', 'query', name="search"),
#   url (r'^mine/$', 'mine', name="mine"),
#   url (r'^myapprovals/$', 'myapprovals', name="myapprovals"),
)
