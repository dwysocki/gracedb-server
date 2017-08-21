
# Changed for Django 1.11 upgrade
from django.conf.urls import url, include
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from gracedb.feeds import EventFeed, feedview

# After Django 1.10, have to import views directly, rather
# than just using a string
import gracedb.views
import gracedb.reports

feeds = {
    'latest' : EventFeed
}

urlpatterns = [
    url(r'^$', gracedb.views.index, name="home"),
    url(r'^navbar_only$', gracedb.views.navbar_only, name="navbar-only"),
    url(r'^SPInfo', gracedb.views.spinfo, name="spinfo"),
    url(r'^SPPrivacy', gracedb.views.spprivacy, name="spprivacy"),
    url(r'^DiscoveryService', gracedb.views.discovery, name="discovery"),
    url(r'^events/', include('gracedb.urls')),
    url(r'^api/',    include('gracedb.urls_rest', app_name="api", namespace="x509")),
    url(r'^apiweb/', include('gracedb.urls_rest', app_name="api", namespace="shib")),
    url(r'^apibasic/', include('gracedb.urls_rest', app_name="api", namespace="basic")),
    url(r'^options/', include('userprofile.urls')),
    url(r'^feeds/(?P<url>.*)/$', EventFeed()),
    url(r'^feeds/$', feedview, name="feeds"),

    url(r'^performance/$', gracedb.views.performance, name="performance"),
    url(r'^reports/$', gracedb.reports.histo, name="reports"),
    url(r'^reports/cbc_report/(?P<format>(json|flex))?$',
        gracedb.reports.cbc_report, name="cbc_report"),
    url(r'^latest', gracedb.views.latest, name="latest"),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),


    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', admin.site.urls),

    # For development only.  And only for old Django versions (like 1.2)
    #(r'^gracedb-static/(?P<path>.*)$', 'django.views.static.serve',
    #    {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    import debug_toolbar
    import debug_panel.views
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^__debug__/data/(?P<cache_key>\d+\.\d+)/$',
            debug_panel.views.debug_data, name='debug_data'),
    ] + urlpatterns
