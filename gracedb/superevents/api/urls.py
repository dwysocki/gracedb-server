from django.conf.urls import url, include

from .views import *
from .settings import SUPEREVENT_LOOKUP_REGEX

# URL kwarg for superevent detail and nested pages
SUPEREVENT_DETAIL_ROOT = '(?P<{lookup_field}>{regex})'.format(
    lookup_field=SupereventViewSet.lookup_field,
    regex=SUPEREVENT_LOOKUP_REGEX)

# URLs which are nested below a single superevent detail
# These are included under a superevent's id URL prefix (see below)
suburlpatterns = [
    # Superevent detail and update
    url(r'^$', SupereventViewSet.as_view({'get': 'retrieve',
        'patch': 'partial_update'}), name='superevent-detail'),
    # Superevent GW confirmation
    url(r'^confirm_as_gw/$', SupereventViewSet.as_view(
        {'post': 'confirm_as_gw'}), name='superevent-confirm-as-gw'),

    # Event list and create (add event to superevent)
    url(r'^events/$', SupereventEventViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-event-list'),
    # Event detail and delete (remove from superevent)
    url(r'^events/(?P<{lookup_field}>[GEHMT]\d+)/$'.format(lookup_field=
        SupereventEventViewSet.lookup_field), SupereventEventViewSet.as_view({
        'get': 'retrieve', 'delete': 'destroy'}),
        name='superevent-event-detail'),

    # Labelling list/create
    url(r'^labels/$', SupereventLabelViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-label-list'),
    # Labelling detail/delete
    url(r'^labels/(?P<{lookup_field}>.+)/$'.format(lookup_field=
        SupereventLabelViewSet.lookup_field), SupereventLabelViewSet.as_view({
        'get': 'retrieve', 'delete': 'destroy'}),
        name='superevent-label-detail'),

    # Log list/create
    url(r'^logs/$', SupereventLogViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-log-list'),
    # Log detail
    url(r'^logs/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventLogViewSet.lookup_field), SupereventLogViewSet.as_view({
        'get': 'retrieve'}), name='superevent-log-detail'),
    # Tag list (for log) and create
    url(r'^logs/(?P<{lookup_field}>\d+)/tags/$'.format(lookup_field=
        SupereventLogViewSet.lookup_field), SupereventLogTagViewSet.as_view({
        'get': 'list', 'post': 'create'}), name='superevent-log-tag-list'),
    # Tag detail/delete
    url(r'^logs/(?P<{log_lookup}>\d+)/tags/(?P<{tag_lookup}>.+)/$'.format(
        log_lookup=SupereventLogViewSet.lookup_field, tag_lookup=
        SupereventLogTagViewSet.lookup_field),
        SupereventLogTagViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'}), name='superevent-log-tag-detail'),

    # File list
    url(r'^files/$', SupereventFileViewSet.as_view({'get': 'list',}),
        name='superevent-file-list'),
    # File detail (download)
    url(r'^files/(?P<{lookup_field}>.+)$'.format(lookup_field=
        SupereventFileViewSet.lookup_field), SupereventFileViewSet.as_view({
        'get': 'retrieve'}), name='superevent-file-detail'),
    # Note: no option for POST since file uploads should be handled
    # by writing a log message

    # VOEvent list/create
    url(r'^voevents/$', SupereventVOEventViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-voevent-list'),
    # VOEvent detail
    url(r'^voevents/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventVOEventViewSet.lookup_field),
        SupereventVOEventViewSet.as_view({'get': 'retrieve'}),
        name='superevent-voevent-detail'),

    # EMObservation list/create
    url(r'^emobservations/$', SupereventEMObservationViewSet.as_view(
        {'get': 'list', 'post': 'create'}),
        name='superevent-emobservation-list'),
    # EMObservation detail
    url(r'^emobservations/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventEMObservationViewSet.lookup_field),
        SupereventEMObservationViewSet.as_view({'get': 'retrieve'}),
        name='superevent-emobservation-detail'),
]

# Full urlpatterns
urlpatterns = [

    # Superevent list and create
    url(r'^$', SupereventViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='superevent-list'),

    # All sub-URLs for a single superevent
    url(r'^{superevent_id}/'.format(superevent_id=SUPEREVENT_DETAIL_ROOT),
        include(suburlpatterns)),
]
