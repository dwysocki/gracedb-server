from django.conf.urls import url, include

from .views import * 


urlpatterns = [
    # Event Resources
    # events/[{graceid}[/{version}]]
    url(r'^$', EventList.as_view(), name='event-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)$', EventDetail.as_view(),
        name='event-detail'),

    # Event Log Resources
    # events/{graceid}/logs/[{logid}]
    url(r'^(?P<graceid>[GEHMT]\d+)/log/$', EventLogList.as_view(),
        name='eventlog-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)$',
        EventLogDetail.as_view(), name='eventlog-detail'),

    # VOEvent Resources
    # events/{graceid}/voevent/[{serial_number}]
    url(r'^(?P<graceid>[GEHMT]\d+)/voevent/$', VOEventList.as_view(),
        name='voevent-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/voevent/(?P<n>\d+)$',
        VOEventDetail.as_view(), name='voevent-detail'),

    # EMBB Resources
    # events/{graceid}/logs/[{logid}]
    url(r'^(?P<graceid>[GEHMT]\d+)/embb/$', EMBBEventLogList.as_view(),
        name='embbeventlog-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/embb/(?P<n>\d+)$',
        EMBBEventLogDetail.as_view(), name='embbeventlog-detail'),
    url(r'^(?P<graceid>[GEHMT]\d+)/emobservation/$',
        EMObservationList.as_view(), name='emobservation-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)$',
        EMObservationDetail.as_view(), name='emobservation-detail'),
#    url(r'(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)/emfootprint/$',
#        EMFootprintList.as_view(), name='emfootprint-list'),
#    url(r'(?P<graceid>[GEHMT]\d+)/emobservation/(?P<n>\d+)/emfootprint/(?P<m>\d+)$',
#        EMFootprintDetail.as_view(), name='emfootprint-detail'),

    # Tag Resources
    url(r'^(?P<graceid>[GEHMT]\d+)/tag/$', EventTagList.as_view(),
        name='eventtag-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/tag/(?P<tagname>.+)$',
        EventTagDetail.as_view(), name='eventtag-detail'),
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)/tag/$',
        EventLogTagList.as_view(), name='eventlogtag-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<n>\d+)/tag/(?P<tagname>.+)$',
        EventLogTagDetail.as_view(), name='eventlogtag-detail'),

    # Permission Resources
    url(r'^(?P<graceid>[GEHMT]\d+)/perms/$',
        EventPermissionList.as_view(), name='eventpermission-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/perms/(?P<group_name>.+)/$', 
        GroupEventPermissionList.as_view(), name='groupeventpermission-list'),
    url(r'^(?P<graceid>[GEHMT]\d+)/perms/(?P<group_name>.+)/(?P<perm_shortname>\w+)$', 
        GroupEventPermissionDetail.as_view(), name='groupeventpermission-detail'),

    # Event File Resources
    # events/{graceid}/files/[{filename}[/{version}]]
    url(r'^(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$',
        Files.as_view(), name="files"),

    # Event Labels
    # events/{graceid}/labels/[{label}]
    url(r'^(?P<graceid>\w[\d]+)/labels/(?P<label>.+)?$',
        EventLabel.as_view(), name="labels"),

    # Event Neighbors
    # events/{graceid}/neighbors/[?delta=(N|(N,N))]
    url(r'^(?P<graceid>\w[\d]+)/neighbors/$', EventNeighbors.as_view(),
        name="neighbors"),

    # Operator Signoff Resources
    url(r'^(?P<graceid>[GEHMT]\d+)/signoff/$',
        OperatorSignoffList.as_view(), name='signoff-list'),

]
