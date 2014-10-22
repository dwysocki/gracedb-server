
# Changed for Django 1.6
from django.conf.urls import patterns, url
#from django.conf.urls.defaults import patterns, url

# rest_framework
from gracedb.api import GracedbRoot
from gracedb.api import EventList, EventDetail, EventVODetail
from gracedb.api import EventLogList, EventLogDetail
from gracedb.api import TagList
# from gracedb.api import TagDetail
from gracedb.api import EventTagList, EventTagDetail
from gracedb.api import EventLogTagList, EventLogTagDetail
from gracedb.api import Files, FileMeta
from gracedb.api import EventNeighbors, EventLabel
from gracedb.api import PerformanceInfo
from gracedb.api import EventPermissionList
from gracedb.api import GroupEventPermissionList
from gracedb.api import GroupEventPermissionDetail


urlpatterns = patterns('gracedb.api',
    url (r'^/?$', GracedbRoot.as_view(), name="api-root"),


    # Event Resources
    # events/[{graceid}[/{version}]]
    url (r'events/$',
        EventList.as_view(), name='event-list'),
    url (r'events/voevent/(?P<graceid>[GEHT]\d+)$',
        EventVODetail.as_view(), name='event-vo-detail'),
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

    # Permission Resources
    url (r'events/(?P<graceid>[GEHT]\d+)/perms/$',
        EventPermissionList.as_view(), name='eventpermission-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/perms/(?P<group_name>.+)/$', 
        GroupEventPermissionList.as_view(), name='groupeventpermission-list'),
    url (r'events/(?P<graceid>[GEHT]\d+)/perms/(?P<group_name>.+)/(?P<perm_shortname>\w+)$', 
        GroupEventPermissionDetail.as_view(), name='groupeventpermission-detail'),

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

    # Event Neighbors
    # events/{graceid}/neighbors/[?delta=(N|(N,N))]
    url (r'^events/(?P<graceid>\w[\d]+)/neighbors/$',
        EventNeighbors.as_view(), name="neighbors"),

    # Performance stats
    url (r'^performance/$', 
        PerformanceInfo.as_view(), name='performance-info'),

    # Legacy
    #url (r'^events/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', 'download', name="files"),
    url (r'^event/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', 'download', name="download2"),
)
