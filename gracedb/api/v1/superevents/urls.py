from django.urls import re_path, include
from django.urls import path
from django.views.decorators.cache import never_cache

from .views import *
from .settings import SUPEREVENT_LOOKUP_REGEX


# URL kwarg for superevent detail and nested pages
SUPEREVENT_DETAIL_ROOT = '<{lookup_url_kwarg}>'.format(
    lookup_url_kwarg=SupereventViewSet.lookup_url_kwarg)

# URLs which are nested below a single superevent detail
# These are included under a superevent's id URL prefix (see below)
suburlpatterns = [
    # Superevent detail and update
    re_path(r'^$', never_cache(SupereventViewSet.as_view({'get': 'retrieve',
        'patch': 'partial_update'})), name='superevent-detail'),
    # Superevent GW confirmation
    re_path(r'^confirm-as-gw/$', never_cache(SupereventViewSet.as_view(
        {'post': 'confirm_as_gw'})), name='superevent-confirm-as-gw'),

    # Event list and creation (addition to superevent)
    re_path(r'^events/$', never_cache(SupereventEventViewSet.as_view({'get': 'list',
        'post': 'create'})), name='superevent-event-list'),
    # Event detail and delete (remove from superevent)
    re_path(r'^events/(?P<{lookup_url_kwarg}>[GEHMT]\d+)/$'.format(
        lookup_url_kwarg=SupereventEventViewSet.lookup_url_kwarg),
        never_cache(SupereventEventViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'})), name='superevent-event-detail'),

    # Pipeline preferred event list and creation 
    re_path(r'^pipeline_preferred_events/$', never_cache(SupereventPipelinePreferredEventViewSet.as_view({'get': 'list',
        'post': 'create'})), name='superevent-pipeline-preferred-event-list'),
    # Event detail and delete (remove from superevent)
    re_path(r'^pipeline_preferred_events/(?P<{lookup_url_kwarg}>[GEHMT]\d+)/$'.format(
        lookup_url_kwarg=SupereventPipelinePreferredEventViewSet.lookup_url_kwarg),
        never_cache(SupereventPipelinePreferredEventViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'})), name='superevent-pipeline-preferred-event-detail'),

    # Labelling list and creation
    re_path(r'^labels/$', never_cache(SupereventLabelViewSet.as_view({'get': 'list',
        'post': 'create'})), name='superevent-label-list'),
    # Labelling detail and deletion
    re_path(r'^labels/(?P<{lookup_url_kwarg}>.+)/$'.format(lookup_url_kwarg=
        SupereventLabelViewSet.lookup_url_kwarg),
        never_cache(SupereventLabelViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'})), name='superevent-label-detail'),

    # Log list and creation
    re_path(r'^logs/$', never_cache(SupereventLogViewSet.as_view({'get': 'list',
        'post': 'create'})), name='superevent-log-list'),
    # Log detail
    re_path(r'^logs/(?P<{lookup_url_kwarg}>\d+)/$'.format(lookup_url_kwarg=
        SupereventLogViewSet.lookup_url_kwarg), never_cache(SupereventLogViewSet.as_view({
        'get': 'retrieve'})), name='superevent-log-detail'),
    # Tag list (for log) and creation (addition of tag to log)
    re_path(r'^logs/(?P<{lookup_url_kwarg}>\d+)/tags/$'.format(
        lookup_url_kwarg=SupereventLogViewSet.lookup_url_kwarg),
        never_cache(SupereventLogTagViewSet.as_view({'get': 'list', 'post': 'create'})),
        name='superevent-log-tag-list'),
    # Tag detail and deletion (removal of tag from log)
    re_path(r'^logs/(?P<{log_lookup}>\d+)/tags/(?P<{tag_lookup}>.+)/$'.format(
        log_lookup=SupereventLogViewSet.lookup_url_kwarg, tag_lookup=
        SupereventLogTagViewSet.lookup_url_kwarg),
        never_cache(SupereventLogTagViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'})), name='superevent-log-tag-detail'),

    # File list
    re_path(r'^files/$', SupereventFileViewSet.as_view({'get': 'list',}),
        name='superevent-file-list'),
    # File detail (download)
    re_path(r'^files/(?P<{lookup_url_kwarg}>.+)$'.format(lookup_url_kwarg=
        SupereventFileViewSet.lookup_url_kwarg), SupereventFileViewSet.as_view(
        {'get': 'retrieve'}), name='superevent-file-detail'),
    # Note: no option for POST since file uploads should be handled
    # by writing a log message

    # VOEvent list and creation
    re_path(r'^voevents/$', never_cache(SupereventVOEventViewSet.as_view({'get': 'list',
        'post': 'create'})), name='superevent-voevent-list'),
    # VOEvent detail
    re_path(r'^voevents/(?P<{lookup_url_kwarg}>\d+)/$'.format(lookup_url_kwarg=
        SupereventVOEventViewSet.lookup_url_kwarg),
        never_cache(SupereventVOEventViewSet.as_view({'get': 'retrieve'})),
        name='superevent-voevent-detail'),

    # EMObservation list and creation
    re_path(r'^emobservations/$', never_cache(SupereventEMObservationViewSet.as_view(
        {'get': 'list', 'post': 'create'})),
        name='superevent-emobservation-list'),
    # EMObservation detail
    re_path(r'^emobservations/(?P<{lookup_url_kwarg}>\d+)/$'.format(
        lookup_url_kwarg=SupereventEMObservationViewSet.lookup_url_kwarg),
        never_cache(SupereventEMObservationViewSet.as_view({'get': 'retrieve'})),
        name='superevent-emobservation-detail'),

    # Signoff list and creation
    re_path(r'signoffs/$', never_cache(SupereventSignoffViewSet.as_view(
        {'get': 'list', 'post': 'create'})), name='superevent-signoff-list'),
    # Signoff detail
    re_path(r'signoffs/(?P<{lookup_url_kwarg}>.+)/$'.format(lookup_url_kwarg=
        SupereventSignoffViewSet.lookup_url_kwarg),
        never_cache(SupereventSignoffViewSet.as_view({'get': 'retrieve',
        'patch': 'partial_update', 'delete': 'destroy'})),
        name='superevent-signoff-detail'),

    # Permissions list and creation
    re_path(r'permissions/$', never_cache(SupereventGroupObjectPermissionViewSet.as_view(
        {'get': 'list'})), name='superevent-permission-list'),
    # Permissions modification (expose/hide superevent).
    re_path(r'^permissions/modify/$',
        never_cache(SupereventGroupObjectPermissionViewSet.as_view({'post': 'modify'})),
        name='superevent-permission-modify'),
]

# Full urlpatterns
urlpatterns = [

    # Superevent list and creation
    re_path(r'^$', never_cache(SupereventViewSet.as_view({'get': 'list', 'post': 'create'})),
        name='superevent-list'),

    # All sub-URLs for a single superevent
    path('{superevent_id}/'.format(superevent_id=SUPEREVENT_DETAIL_ROOT),
        include(suburlpatterns)),
]
