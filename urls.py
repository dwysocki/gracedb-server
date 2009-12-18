from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from gracedb.feeds import EventFeed, feedview

feeds = {
    'latest' : EventFeed
}

urlpatterns = patterns('',

    url (r'^$', 'gracedb.gracedb.views.index', name="home"),
    (r'^events/', include('gracedb.gracedb.urls')),
    url (r'^doc/', 'gracedb.gracedb.doc.index', name="doc"),
    (r'^options/', include('gracedb.userprofile.urls')),
    (r'^cli/create', 'gracedb.gracedb.views.create'),
    (r'^cli/ping', 'gracedb.gracedb.views.ping'),
    (r'^cli/log', 'gracedb.gracedb.views.log'),
    (r'^cli/upload', 'gracedb.gracedb.views.upload'),
    (r'^cli/tag', 'gracedb.gracedb.views.cli_tag'),
    (r'^cli/label', 'gracedb.gracedb.views.cli_label'),
    (r'^cli/search', 'gracedb.gracedb.views.cli_search'),
    #(r'^cli/ping/(?P<arg>.*)', 'gracedb.gracedb.views.ping'),
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', 
        {'feed_dict': feeds}),
    url (r'^feeds/$', feedview, name="feeds"),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),

)
