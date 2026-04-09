"""
v2 event URL patterns.

Re-exports v1 URL patterns with two changes:
  1. The event-list URL (GET list, POST create) uses the v2 EventList view
     so that the v2 search filter is active.
  2. Adds POST /search/ for body-based structured queries.

All other event sub-routes (detail, logs, files, labels, etc.) remain v1.
"""
from django.urls import re_path
from django.views.decorators.cache import never_cache

# All v1 event URL patterns except the list endpoint.
from ...v1.events.urls import urlpatterns as _v1_event_patterns

# v2 views: EventList (with v2 GET filter) and EventSearch (POST body).
from .views import EventList, EventSearch

# Rebuild the list: replace the event-list pattern with v2; keep everything else.
urlpatterns = [
    p for p in _v1_event_patterns
    if getattr(p, 'name', None) != 'event-list'
]

urlpatterns = [
    # GET /events/ — v2 list with ?query=<json> support
    # POST /events/ — event creation (v1 logic, inherited by EventList)
    re_path(
        r'^$',
        never_cache(EventList.as_view()),
        name='event-list',
    ),

    # POST /events/search/ — body-based structured query
    re_path(
        r'^search/$',
        never_cache(EventSearch.as_view()),
        name='event-search',
    ),
] + urlpatterns
