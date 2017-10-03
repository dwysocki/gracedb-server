
# Changed for Django 1.11
from django.conf.urls import url

# rest_framework
from gracedb.api import GracedbRoot
from gracedb.api import EventList, EventDetail
from gracedb.api import EventLogList, EventLogDetail
from gracedb.api import EMBBEventLogList, EMBBEventLogDetail
from gracedb.api import EMObservationList, EMObservationDetail
#from gracedb.api import EMFootprintList, EMFootprintDetail
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
from gracedb.api import VOEventList, VOEventDetail
from gracedb.api import OperatorSignoffList
from gracedb.api import download as download_view

urlpatterns = [
    url(r'^$', GracedbRoot.as_view(), name="api-root"),

    # Event Resources
    # events/[{graceid}[/{version}]]
    url(r'events/$',
        EventList.as_view(), name='event-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)$',
        EventDetail.as_view(), name='event-detail'),

    # Event Log Resources
    # events/{graceid}/logs/[{logid}]
    url(r'events/(?P<graceid>[GEHMT]\d+)/log/$',
        EventLogList.as_view(), name='eventlog-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)$',
        EventLogDetail.as_view(), name='eventlog-detail'),

    # VOEvent Resources
    # events/{graceid}/voevent/[{serial_number}]
    url(r'events/(?P<graceid>[GEHMT]\d+)/voevent/$',
        VOEventList.as_view(), name='voevent-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/voevent/(?P<n>\d+)$',
        VOEventDetail.as_view(), name='voevent-detail'),

    # EMBB Resources
    # events/{graceid}/logs/[{logid}]
    url(r'events/(?P<graceid>[GEHMT]\d+)/embb/$',
        EMBBEventLogList.as_view(), name='embbeventlog-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/embb/(?P<n>\d+)$',
        EMBBEventLogDetail.as_view(), name='embbeventlog-detail'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/emobservation/$',
        EMObservationList.as_view(), name='emobservation-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)$',
        EMObservationDetail.as_view(), name='emobservation-detail'),
#    url(r'events/(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)/emfootprint/$',
#        EMFootprintList.as_view(), name='emfootprint-list'),
#    url(r'events/(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)/emfootprint/(?P<m>\d+)$',
#        EMFootprintDetail.as_view(), name='emfootprint-detail'),

    # Tag Resources
    url(r'^tag/$', TagList.as_view(), name='tag-list'),
    # XXX unclear what the tag detail resource should be.
    #url(r'^tag/(?P<tagname>.+)$', 
    #    TagDetail.as_view(), name='tag-detail'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/tag/$',
        EventTagList.as_view(), name='eventtag-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/tag/(?P<tagname>.+)$',
        EventTagDetail.as_view(), name='eventtag-detail'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)/tag/$',
        EventLogTagList.as_view(), name='eventlogtag-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)/tag/(?P<tagname>.+)$',
        EventLogTagDetail.as_view(), name='eventlogtag-detail'),

    # Permission Resources
    url(r'events/(?P<graceid>[GEHMT]\d+)/perms/$',
        EventPermissionList.as_view(), name='eventpermission-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/perms/(?P<group_name>.+)/$', 
        GroupEventPermissionList.as_view(), name='groupeventpermission-list'),
    url(r'events/(?P<graceid>[GEHMT]\d+)/perms/(?P<group_name>.+)/(?P<perm_shortname>\w+)$', 
        GroupEventPermissionDetail.as_view(), name='groupeventpermission-detail'),

    # Event File Resources
    # events/{graceid}/files/[{filename}[/{version}]]
    url(r'^events/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$',
        Files.as_view(), name="files"),
    # events/{graceid}/filemeta/[{filename}]
    url(r'^events/(?P<graceid>\w[\d]+)/filemeta/(?P<filename>.+)?$',
        FileMeta.as_view(), name="filemeta"),

    # Event Labels
    # events/{graceid}/labels/[{label}]
    url(r'^events/(?P<graceid>\w[\d]+)/labels/(?P<label>.+)?$',
        EventLabel.as_view(), name="labels"),

    # Event Neighbors
    # events/{graceid}/neighbors/[?delta=(N|(N,N))]
    url(r'^events/(?P<graceid>\w[\d]+)/neighbors/$',
        EventNeighbors.as_view(), name="neighbors"),

    # Operator Signoff Resources
    url(r'events/(?P<graceid>[GEHMT]\d+)/signoff/$',
        OperatorSignoffList.as_view(), name='signoff-list'),


    # Performance stats
    url(r'^performance/$', 
        PerformanceInfo.as_view(), name='performance-info'),

    # Legacy
    #url(r'^events/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', 'download', name="files"),
    url(r'^event/(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$', download_view, name="download2"),
]
