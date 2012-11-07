
from django.conf.urls.defaults import *

from piston.resource import Resource
from gracedb.api import EventHandler

eventHandler = Resource(EventHandler)

urlpatterns = patterns('gracedb.api',
    url (r'^events/[A-Z]?(?P<id>[\w\d]+)$', eventHandler, name="api_event"),
    url (r'^events/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download"),
    url (r'^event/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download2"),
)
