
# Changed for Django 1.6 upgrade
#from django.conf.urls.defaults import *
from django.conf.urls import patterns, url, include
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from gracedb.feeds import EventFeed, feedview

feeds = {
    'latest' : EventFeed
}

urlpatterns = patterns('',

    url (r'^$', 'gracedb.views.index', name="home"),
    url (r'^navbar_only$', 'gracedb.views.navbar_only', name="navbar-only"),
    url (r'^SPInfo', 'gracedb.views.spinfo', name="spinfo"),
    url (r'^SPPrivacy', 'gracedb.views.spprivacy', name="spprivacy"),
    url (r'^DiscoveryService', 'gracedb.views.discovery', name="discovery"),
    (r'^events/', include('gracedb.urls')),
    (r'^api/',    include('gracedb.urls_rest', app_name="api", namespace="x509")),
    (r'^apiweb/', include('gracedb.urls_rest', app_name="api", namespace="shib")),
    (r'^apibasic/', include('gracedb.urls_rest', app_name="api", namespace="basic")),
    (r'^options/', include('userprofile.urls')),
    (r'^cli/create', 'gracedb.views.create'),
    (r'^cli/ping', 'gracedb.cli_views.ping'),
    (r'^cli/log', 'gracedb.cli_views.log'),
    (r'^cli/upload', 'gracedb.cli_views.upload'),
    (r'^cli/tag', 'gracedb.cli_views.cli_tag'),
    (r'^cli/label', 'gracedb.cli_views.cli_label'),
    (r'^cli/search', 'gracedb.cli_views.cli_search'),
    (r'^feeds/(?P<url>.*)/$', EventFeed()),
    url (r'^feeds/$', feedview, name="feeds"),

    url (r'^performance/$', 'gracedb.views.performance', name="performance"),
    url (r'^reports/$', 'gracedb.reports.histo', name="reports"),
    url (r'^reports/cbc_report/(?P<format>(json|flex))?$', 'gracedb.reports.cbc_report', name="cbc_report"),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),

    url (r'^latest', 'gracedb.views.latest', name="latest"),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),

    # For development only.  And only for old Django versions (like 1.2)
    (r'^gracedb-static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),

)
