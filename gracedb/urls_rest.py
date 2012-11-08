
from django.conf.urls.defaults import patterns, url

# rest_framework
from gracedb.api import EventList, EventDetail

urlpatterns = patterns('gracedb.api',
    url (r'^$', 'api_root'),
    # Piston

    # rest_framework
    url (r'^revents/$', EventList.as_view(), name='event-list'),
    url (r'^revents/[GEHT](?P<pk>\d+)$', EventDetail.as_view(), name='event-detail'),

    # Legacy
    url (r'^events/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download"),
    url (r'^event/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download2"),
)
