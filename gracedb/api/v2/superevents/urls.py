"""
v2 superevent URL patterns.

Re-exports v1 URL patterns with two changes:
  1. The superevent-list URL (GET list, POST create) uses the v2 SupereventViewSet
     so that the v2 search filter is active.
  2. Adds POST /search/ for body-based structured queries.
"""
from django.urls import path, re_path, include
from django.views.decorators.cache import never_cache

# Import the v1 patterns (all sub-patterns remain v1 except where we override).
from ...v1.superevents.urls import suburlpatterns
from ...v1.superevents.settings import SUPEREVENT_LOOKUP_URL_KWARG, \
    SUPEREVENT_LOOKUP_REGEX

# Import the v2 SupereventViewSet (has V2SupereventSearchFilter).
from .views import SupereventViewSet

# Full urlpatterns: override the list endpoint to use v2 view; keep
# all sub-patterns (detail, events, labels, logs, etc.) from v1 intact.
urlpatterns = [
    # Superevent list (v2 view for v2 search filter) and creation (v1 logic)
    re_path(
        r'^$',
        never_cache(SupereventViewSet.as_view({'get': 'list', 'post': 'create'})),
        name='superevent-list',
    ),

    # POST /search/ — body-based structured query
    re_path(
        r'^search/$',
        never_cache(SupereventViewSet.as_view({'post': 'search'})),
        name='superevent-search',
    ),

    # All sub-URLs for a single superevent (same as v1)
    path(
        '{superevent_id}/'.format(
            superevent_id='<{lookup_url_kwarg}>'.format(
                lookup_url_kwarg=SUPEREVENT_LOOKUP_URL_KWARG
            )
        ),
        include(suburlpatterns),
    ),
]
