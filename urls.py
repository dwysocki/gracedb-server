
from django.conf.urls.defaults import *
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
    (r'^events/', include('gracedb.urls')),
    (r'^api/', include('gracedb.urls_rest')),
    (r'^options/', include('userprofile.urls')),
    (r'^cli/create', 'gracedb.views.create'),
    (r'^cli/ping', 'gracedb.views.ping'),
    (r'^cli/log', 'gracedb.views.log'),
    (r'^cli/upload', 'gracedb.views.upload'),
    (r'^cli/tag', 'gracedb.views.cli_tag'),
    (r'^cli/label', 'gracedb.views.cli_label'),
    (r'^cli/search', 'gracedb.views.cli_search'),
    (r'^feeds/(?P<url>.*)/$', EventFeed()),
    url (r'^feeds/$', feedview, name="feeds"),

    url (r'^reports/$', 'gracedb.reports.histo', name="reports"),
    (r'^reports/(?P<path>.+)$', 'django.views.static.serve',
            {'document_root': settings.LATENCY_REPORT_DEST_DIR}),

    url (r'^latest', 'gracedb.views.latest', name="latest"),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),

    # For development only.  And only for old Django versions (like 1.2)
    (r'^gracedb-static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),

)
