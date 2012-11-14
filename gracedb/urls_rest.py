
from django.conf.urls.defaults import patterns, url

# rest_framework
from gracedb.api import GracedbRoot
from gracedb.api import EventList, EventDetail
from gracedb.api import EventLogList, EventLogDetail
from gracedb.api import Files, FileMeta

urlpatterns = patterns('gracedb.api',
    url (r'^$', GracedbRoot.as_view(), name="api-root"),

    # Event Resources
    # events/[{graceid}[/{version}]]
    url (r'events/$', EventList.as_view(), name='event-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)$', EventDetail.as_view(), name='event-detail'),
    # Event Log Resources
    # events/{graceid}/logs/[{logid}]
    url (r'events/(?P<graceid>[GEHT]\d+)/log/$', EventLogList.as_view(), name='eventlog-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/log/(?P<n>\d+)$', EventLogDetail.as_view(), name='eventlog-detail'),

    # Event File Resources
    # events/{graceid}/files/[{filename}[/{version}]]
    # XXX change to DjangoRF.  But this works now with the cli.
    #url (r'^events/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="files"),
    url (r'^events/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', Files.as_view(), name="files"),
    # events/{graceid}/filemeta/[{filename}]
    url (r'^events/(?P<graceid>[\w\d]+)/filemeta/(?P<filename>.+)?$', FileMeta.as_view(), name="filemeta"),

    # Event Labels
    # events/{graceid}/labels/[{label}]

    # Event Slots
    # events/{graceid}/slots/[{slotid}]

    # Event Neighbors
    # events/{graceid}/neighbors/[?neighborhood=N]

    # Legacy
    url (r'^event/(?P<graceid>[\w\d]+)/files/(?P<filename>.+)?$', 'download', name="download2"),
)
