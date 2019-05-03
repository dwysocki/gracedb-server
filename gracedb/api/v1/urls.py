from __future__ import absolute_import

from django.conf.urls import url, include

from .main.views import GracedbRoot, PerformanceInfo, TagList, UserInfoView, \
    CertDebug, CertInfosDebug

from .events import urls as event_urls
from .superevents import urls as superevent_urls


urlpatterns = [
    # Root level API resources ------------------------------------------------
    # API root
    url(r'^$', GracedbRoot.as_view(), name="root"),

    # User information
    url(r'^user-info/', UserInfoView.as_view(), name='user-info'),

    # Tags
    url(r'^tag/', TagList.as_view(), name='tag-list'),

    # Performance stats
    url(r'^performance/', PerformanceInfo.as_view(), name='performance-info'),

    # Certificate debugging
    #url(r'^cert-debug/', CertDebug.as_view(), name='cert-debug'),
    #url(r'^cert-infos-debug/', CertInfosDebug.as_view(),
    #    name='cert-infos-debug'),

    # Events section of the API -----------------------------------------------
    url(r'^events/', include((event_urls, 'events'))),

    # Superevents section of the API ------------------------------------------
    url(r'^superevents/', include((superevent_urls, 'superevents'))),
]
