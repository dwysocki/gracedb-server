
# Changed for Django 1.11 upgrade
from django.conf import settings
from django.conf.urls import url, include

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.auth.views import logout
from django.views.generic import TemplateView

# Import feeds
from events.feeds import EventFeed, feedview

# After Django 1.10, have to import views directly, rather
# than just using a string
import events.reports
import events.views
from ligoauth.views import gracedb_login
import search.views

# Django admin auto-discover
admin.autodiscover()

feeds = {
    'latest' : EventFeed
}


urlpatterns = [
    url(r'^$', events.views.index, name="home"),
    url(r'^navbar_only$', TemplateView.as_view(
        template_name='navbar_only.html'), name="navbar-only"),
    url(r'^SPInfo', TemplateView.as_view(template_name='gracedb/spinfo.html'),
         name="spinfo"),
    url(r'^SPPrivacy', TemplateView.as_view(
        template_name='gracedb/spprivacy.html'), name="spprivacy"),
    url(r'^DiscoveryService', TemplateView.as_view(
        template_name='discovery.html'), name="discovery"),
    url(r'^events/', include('events.urls')),
    url(r'^superevents/', include('superevents.urls')),
    url(r'^options/', include('userprofile.urls')),
    url(r'^feeds/(?P<url>.*)/$', EventFeed()),
    url(r'^feeds/$', feedview, name="feeds"),

    url(r'^performance/$', events.views.performance, name="performance"),
    url(r'^reports/$', events.reports.histo, name="reports"),
    url(r'^reports/cbc_report/(?P<format>(json|flex))?$',
        events.reports.cbc_report, name="cbc_report"),
    url(r'^latest/$', search.views.latest, name="latest"),
    url(r'^login/$', gracedb_login, name='login'),
    url(r'^logout/$', logout, {'next_page': '/'}, name='logout'),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),
    url(r'^search/$', search.views.search, name="mainsearch"),

    # API URLs
    url(r'^apibasic/', include('api.urls', namespace="basic")),
    url(r'^apiweb/', include('api.urls', namespace="shib")),
    url(r'^api/', include('api.urls', namespace="x509")),
    #url(r'^apinew/', include('api.urls')), # one place for all auth schemes

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),

]

# We don't require settings.DEBUG for django-silk since running unit tests
# by default setings settings.DEBUG to False, unless you use the
# --debug-mode flag
if ('silk' in settings.INSTALLED_APPS):
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
