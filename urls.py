from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^gracedb/', include('gracedb.foo.urls')),

    (r'^$', 'gracedb.gracedb.views.index'),
    (r'^events/', include('gracedb.gracedb.urls')),
    (r'^cli/create', 'gracedb.gracedb.views.create'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),

)
