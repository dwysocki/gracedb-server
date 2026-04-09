"""
v2 API URL configuration.

Mirrors the v1 structure but uses v2 events and superevents sub-modules
(which add the /search/ endpoint and wire up the v2 filter).
"""
from django.urls import re_path, include

from ..v1 import urls as v1_urls
from .events import urls as event_urls
from .superevents import urls as superevent_urls

# Start with all v1 patterns (root, user-info, tag, performance, gwtc, etc.)
# then override the events and superevents sub-sections with v2 versions.
from ..v1.urls import urlpatterns as _v1_patterns

urlpatterns = [
    p for p in _v1_patterns
    if getattr(p, 'name', None) not in ('event-list', 'superevent-list')
    and not (
        hasattr(p, 'app_name') and p.app_name in ('events', 'superevents')
    )
    and not (
        hasattr(p, 'namespace') and p.namespace in ('events', 'superevents')
    )
]

# Add v2 events and superevents with the correct namespace.
urlpatterns += [
    re_path(r'^events/', include((event_urls, 'events'))),
    re_path(r'^superevents/', include((superevent_urls, 'superevents'))),
]
