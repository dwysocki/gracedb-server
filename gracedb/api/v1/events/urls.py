from django.conf.urls import url, include
# Turn off api caching:
from django.views.decorators.cache import never_cache

from .views import * 


urlpatterns = [
    # Event Resources
    # events/[{graceid}[/{version}]]
    url(r'^$', never_cache(EventList.as_view()), name='event-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)$', never_cache(EventDetail.as_view()),
        name='event-detail'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/update-grbevent/$',
        never_cache(GrbEventPatchView.as_view()), name='update-grbevent'),

    # Event Log Resources
    # events/{graceid}/logs/[{logid}]
    url(r'^(?P<graceid>[GEHMTC]\d+)/log/$', never_cache(EventLogList.as_view()),
        name='eventlog-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/log/(?P<n>\d+)$',
        never_cache(EventLogDetail.as_view()), name='eventlog-detail'),

    # VOEvent Resources
    # events/{graceid}/voevent/[{serial_number}]
    url(r'^(?P<graceid>[GEHMTC]\d+)/voevent/$', never_cache(VOEventList.as_view()),
        name='voevent-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/voevent/(?P<n>\d+)$',
        never_cache(VOEventDetail.as_view()), name='voevent-detail'),

    # EMBB Resources
    # events/{graceid}/logs/[{logid}]
    url(r'^(?P<graceid>[GEHMTC]\d+)/embb/$', never_cache(EMBBEventLogList.as_view()),
        name='embbeventlog-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/embb/(?P<n>\d+)$',
        never_cache(EMBBEventLogDetail.as_view()), name='embbeventlog-detail'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/emobservation/$',
        never_cache(EMObservationList.as_view()), name='emobservation-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/emobservation/(?P<n>\d+)$',
        never_cache(EMObservationDetail.as_view()), name='emobservation-detail'),
#    url(r'(?P<graceid>[GEHMTC]\d+)/emobservation/(?P<n>\d+)/emfootprint/$',
#        EMFootprintList.as_view(), name='emfootprint-list'),
#    url(r'(?P<graceid>[GEHMTC]\d+)/emobservation/(?P<n>\d+)/emfootprint/(?P<m>\d+)$',
#        EMFootprintDetail.as_view(), name='emfootprint-detail'),

    # Tag Resources
    url(r'^(?P<graceid>[GEHMTC]\d+)/tag/$', never_cache(EventTagList.as_view()),
        name='eventtag-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/tag/(?P<tagname>.+)$',
        never_cache(EventTagDetail.as_view()), name='eventtag-detail'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/log/(?P<n>\d+)/tag/$',
        never_cache(EventLogTagList.as_view()), name='eventlogtag-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/log/(?P<n>\d+)/tag/(?P<tagname>.+)$',
        never_cache(EventLogTagDetail.as_view()), name='eventlogtag-detail'),

    # Permission Resources
    url(r'^(?P<graceid>[GEHMTC]\d+)/perms/$',
        never_cache(EventPermissionList.as_view()), name='eventpermission-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/perms/(?P<group_name>.+)/$', 
        never_cache(GroupEventPermissionList.as_view()), name='groupeventpermission-list'),
    url(r'^(?P<graceid>[GEHMTC]\d+)/perms/(?P<group_name>.+)/(?P<perm_shortname>\w+)$', 
        never_cache(GroupEventPermissionDetail.as_view()), name='groupeventpermission-detail'),

    # Event File Resources
    # events/{graceid}/files/[{filename}[/{version}]]
    url(r'^(?P<graceid>\w[\d]+)/files/(?P<filename>.+)?$',
        never_cache(Files.as_view()), name="files"),

    # Event Labels
    # events/{graceid}/labels/[{label}]
    url(r'^(?P<graceid>\w[\d]+)/labels/(?P<label>.+)?$',
        never_cache(EventLabel.as_view()), name="labels"),

    # Event Neighbors
    # events/{graceid}/neighbors/[?delta=(N|(N,N))]
    url(r'^(?P<graceid>\w[\d]+)/neighbors/$', never_cache(EventNeighbors.as_view()),
        name="neighbors"),

    # Operator Signoff Resources
    url(r'^(?P<graceid>[GEHMTC]\d+)/signoff/$',
        never_cache(OperatorSignoffList.as_view()), name='signoff-list'),

]
