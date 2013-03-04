
from django.conf.urls.defaults import patterns, url

# rest_framework
from gracedb.api import GracedbRoot
from gracedb.api import EventList, EventDetail
from gracedb.api import EventLogList, EventLogDetail
from gracedb.api import TagList
# from gracedb.api import TagDetail
from gracedb.api import EventTagList, EventTagDetail
from gracedb.api import EventLogTagList, EventLogTagDetail
from gracedb.api import EventSlot
from gracedb.api import Files, FileMeta
from gracedb.api import EventNeighbors, EventLabel

urlpatterns = patterns('gracedb.api',
    url (r'^/?$', GracedbRoot.as_view(), name="api-root"),


    # Event Resources
    # events/[{graceid}[/{version}]]
    url (r'events/$',
        EventList.as_view(), name='event-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)$',
        EventDetail.as_view(), name='event-detail'),

    # Event Log Resources
    # events/{graceid}/logs/[{logid}]
    url (r'events/(?P<graceid>[GEHT]\d+)/log/$',
        EventLogList.as_view(), name='eventlog-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/log/(?P<n>\d+)$',
        EventLogDetail.as_view(), name='eventlog-detail'),

    # Tag Resources
    url (r'^tag/$', 
        TagList.as_view(), name='tag-list'),
    # XXX unclear what the tag detail resource should be.
    #url (r'^tag/(?P<tagname>\w+)$', 
    #    TagDetail.as_view(), name='tag-detail'),
    url (r'events/(?P<graceid>[GEHT]\d+)/tag/$',
        EventTagList.as_view(), name='eventtag-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/tag/(?P<tagname>\w+)$',
        EventTagDetail.as_view(), name='eventtag-detail'),
    url (r'events/(?P<graceid>[GEHT]\d+)/log/(?P<n>\d+)/tag/$',
        EventLogTagList.as_view(), name='eventlogtag-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/log/(?P<n>\d+)/tag/(?P<tagname>\w+)$',
        EventLogTagDetail.as_view(), name='eventlogtag-detail'),

    # Event File Resources
    # events/{graceid}/files/[{filename}[/{version}]]
    url (r'^events/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$',
        Files.as_view(), name="files"),
    # events/{graceid}/filemeta/[{filename}]
    url (r'^events/(?P<graceid>\w[\d]+)/filemeta/(?P<filename>.+)?$',
        FileMeta.as_view(), name="filemeta"),

    # Event Labels
    # events/{graceid}/labels/[{label}]
    url (r'^events/(?P<graceid>\w[\d]+)/labels/(?P<label>.+)?$',
        EventLabel.as_view(), name="labels"),

    # Event Slots
    # events/{graceid}/slot/[{slotname}]
    url (r'^events/(?P<graceid>[GEHT]\d+)/slot/(?P<slotname>.+)?$',
        EventSlot.as_view(), name="slot"),

    # Event Neighbors
    # events/{graceid}/neighbors/[?delta=(N|(N,N))]
    url (r'^events/(?P<graceid>\w[\d]+)/neighbors/$',
        EventNeighbors.as_view(), name="neighbors"),

    # Legacy
    #url (r'^events/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', 'download', name="files"),
    url (r'^event/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', 'download', name="download2"),
)
