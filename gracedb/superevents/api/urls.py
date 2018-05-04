# Changed for Django 1.11
from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()

# Base URLs for managing superevents
router.register(r'', SupereventViewSet)

# Provides '{superevent_id}/' prefix for URLs
SUPEREVENT_DETAIL_ROOT = router.get_lookup_regex(SupereventViewSet)

# URLs which are nested below a single superevent detail
# These are included under a superevent's id URL prefix (see below)
suburlpatterns = [
    # Events
    url(r'^events/$', SupereventEventViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-event-list'),
    url(r'^events/(?P<{lookup_field}>[GEHMT]\d+)/$'.format(lookup_field=
        SupereventEventViewSet.lookup_field), SupereventEventViewSet.as_view({
        'get': 'retrieve', 'delete': 'destroy'}),
        name='superevent-event-detail'),

    # Labels
    url(r'^labels/$', SupereventLabelViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-label-list'),
    url(r'^labels/(?P<{lookup_field}>.+)/$'.format(lookup_field=
        SupereventLabelViewSet.lookup_field), SupereventLabelViewSet.as_view({
        'get': 'retrieve', 'delete': 'destroy'}),
        name='superevent-label-detail'),

    # Logs and tags
    url(r'^logs/$', SupereventLogViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-log-list'),
    url(r'^logs/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventLogViewSet.lookup_field), SupereventLogViewSet.as_view({
        'get': 'retrieve'}), name='superevent-log-detail'),
    url(r'^logs/(?P<{lookup_field}>\d+)/tags/$'.format(lookup_field=
        SupereventLogViewSet.lookup_field), SupereventLogTagViewSet.as_view({
        'get': 'list', 'post': 'create'}), name='superevent-log-tag-list'),
    url(r'^logs/(?P<{log_lookup}>\d+)/tags/(?P<{tag_lookup}>.+)/$'.format(
        log_lookup=SupereventLogViewSet.lookup_field, tag_lookup=
        SupereventLogTagViewSet.lookup_field),
        SupereventLogTagViewSet.as_view({'get': 'retrieve',
        'delete': 'destroy'}), name='superevent-log-tag-detail'),

    # Files - no option for POST since file uploads should be handled
    # by writing a log message
    url(r'^files/$', SupereventFileViewSet.as_view({'get': 'list',}),
        name='superevent-file-list'),
    url(r'^files/(?P<{lookup_field}>.+)$'.format(lookup_field=
        SupereventFileViewSet.lookup_field), SupereventFileViewSet.as_view({
        'get': 'retrieve'}), name='superevent-file-detail'),

    # VOEvents
    url(r'^voevents/$', SupereventVOEventViewSet.as_view({'get': 'list',
        'post': 'create'}), name='superevent-voevent-list'),
    url(r'^voevents/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventVOEventViewSet.lookup_field),
        SupereventVOEventViewSet.as_view({'get': 'retrieve'}),
        name='superevent-voevent-detail'),

    # EMObservations
    url(r'^emobservations/$', SupereventEMObservationViewSet.as_view(
        {'get': 'list', 'post': 'create'}),
        name='superevent-emobservation-list'),
    url(r'^emobservations/(?P<{lookup_field}>\d+)/$'.format(lookup_field=
        SupereventEMObservationViewSet.lookup_field),
        SupereventEMObservationViewSet.as_view({'get': 'retrieve'}),
        name='superevent-emobservation-detail'),
]

urlpatterns = router.urls + [
    url(r'^{superevent_id}/'.format(superevent_id=SUPEREVENT_DETAIL_ROOT),
        include(suburlpatterns)),
]

