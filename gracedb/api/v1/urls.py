from __future__ import absolute_import

from django.urls import re_path, include

from .main.views import GracedbRoot, PerformanceInfo, TagList, UserInfoView, \
    CertDebug, CertInfosDebug

from .events import urls as event_urls
from .superevents import urls as superevent_urls
from .gwtc import urls as gwtc_urls

# Turn off api caching:
from django.views.decorators.cache import never_cache


urlpatterns = [
    # Root level API resources ------------------------------------------------
    # API root
    re_path(r'^$', never_cache(GracedbRoot.as_view()), name="root"),

    # User information
    re_path(r'^user-info/', never_cache(UserInfoView.as_view()), name='user-info'),

    # Tags
    re_path(r'^tag/', never_cache(TagList.as_view()), name='tag-list'),

    # Performance stats
    re_path(r'^performance/', never_cache(PerformanceInfo.as_view()), name='performance-info'),

    # Certificate debugging
    #re_path(r'^cert-debug/', CertDebug.as_view(), name='cert-debug'),
    #re_path(r'^cert-infos-debug/', CertInfosDebug.as_view(),
    #    name='cert-infos-debug'),

    # Events section of the API -----------------------------------------------
    re_path(r'^events/', include((event_urls, 'events'))),

    # Superevents section of the API ------------------------------------------
    re_path(r'^superevents/', include((superevent_urls, 'superevents'))),

    # Catalog section of the API ----------------------------------------------
    re_path(r'^gwtc/', include((gwtc_urls, 'gwtc'))),
]
