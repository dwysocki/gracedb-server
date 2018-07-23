from __future__ import absolute_import

from django.conf.urls import url, include

from .main.views import GracedbRoot, PerformanceInfo, TagList


urlpatterns = [
    # Root level API resources ------------------------------------------------
    # API root
    url(r'^$', GracedbRoot.as_view(), name="root"),

    # Tags
    url(r'^tag/', TagList.as_view(), name='tag-list'),

    # Performance stats
    url(r'^performance/', PerformanceInfo.as_view(), name='performance-info'),

    # Events section of the API -----------------------------------------------
    url(r'^events/', include('api.v1.events.urls',
        namespace='events')),

    # Superevents section of the API ------------------------------------------
    url(r'^superevents/', include('api.v1.superevents.urls',
        namespace='superevents')),
]
