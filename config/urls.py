
# Changed for Django 1.11 upgrade
from django.conf.urls import url, include
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# Import feeds
from events.feeds import EventFeed, feedview

# After Django 1.10, have to import views directly, rather
# than just using a string
import events.views
import events.reports

feeds = {
    'latest' : EventFeed
}

urlpatterns = [
    url(r'^$', events.views.index, name="home"),
    url(r'^navbar_only$', events.views.navbar_only, name="navbar-only"),
    url(r'^SPInfo', events.views.spinfo, name="spinfo"),
    url(r'^SPPrivacy', events.views.spprivacy, name="spprivacy"),
    url(r'^DiscoveryService', events.views.discovery, name="discovery"),
    url(r'^events/', include('events.urls')),
    url(r'^options/', include('userprofile.urls')),
    url(r'^feeds/(?P<url>.*)/$', EventFeed()),
    url(r'^feeds/$', feedview, name="feeds"),

    url(r'^performance/$', events.views.performance, name="performance"),
    url(r'^reports/$', events.reports.histo, name="reports"),
    url(r'^reports/cbc_report/(?P<format>(json|flex))?$',
        events.reports.cbc_report, name="cbc_report"),
    url(r'^latest', events.views.latest, name="latest"),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),

    # API URLs
    url(r'^apiweb/', include('events.api.urls', app_name="api",
        namespace="shib")),
    url(r'^api/', include('events.api.urls', app_name="api",
        namespace="x509")),
    url(r'^apibasic/', include('events.api.urls', app_name="api",
        namespace="basic")),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', admin.site.urls),

]

# We don't require settings.DEBUG for django-silk since running unit tests
# by default setings settings.DEBUG to False, unless you use the
# --debug-mode flag
if settings.DEBUG or ('silk' in settings.INSTALLED_APPS and
   ['silk' in m for m in settings.MIDDLEWARE]):
    # Add django-silk
    urlpatterns = [
        url(r'^silk/', include('silk.urls', namespace='silk'))
    ] + urlpatterns

# Add django-debug-toolbar
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
