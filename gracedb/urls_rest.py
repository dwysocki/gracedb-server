
from django.conf.urls.defaults import *

urlpatterns = patterns('gracedb.api',
    url (r'^events/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download"),
)
