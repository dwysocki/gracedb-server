from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from gracedb.feeds import EventFeed, feedview

feeds = {
    'latest' : EventFeed
}

urlpatterns = patterns('',

    (r'^$', 'gracedb.gracedb.views.index'),
    (r'^events/', include('gracedb.gracedb.urls')),
    (r'^cli/create', 'gracedb.gracedb.views.create'),
    (r'^cli/ping', 'gracedb.gracedb.views.ping'),
    (r'^cli/log', 'gracedb.gracedb.views.log'),
    (r'^cli/upload', 'gracedb.gracedb.views.upload'),
    #(r'^cli/ping/(?P<arg>.*)', 'gracedb.gracedb.views.ping'),
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', 
        {'feed_dict': feeds}),
    (r'^feeds/$', feedview),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),

)
