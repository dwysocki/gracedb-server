
from django.conf.urls.defaults import *

#import django.views.generic.list_detail

urlpatterns = patterns('gracedb.gracedb.views',
    url (r'^$', 'index', name="home"),
    url (r'^create/$', 'create', name="create"),
    url (r'^search/(?P<format>(json|flex))?$', 'search', name="search"),
    url (r'^view/(?P<graceid>[\w\d]+)', 'view', name="view"),

#   (r'^view/(?P<uid>[\w\d]+)', 'view'),
#   (r'^edit/(?P<uid>[\w\d]+)', 'edit'),
#   (r'^request_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'request_archive'),
#   (r'^approve_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'approve_archive'),
#   url (r'^query', 'query', name="search"),
#   url (r'^mine/$', 'mine', name="mine"),
#   url (r'^myapprovals/$', 'myapprovals', name="myapprovals"),
)
