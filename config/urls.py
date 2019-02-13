from django.conf import settings
from django.conf.urls import url, include

from django.contrib import admin
from django.contrib.auth.views import logout
from django.views.generic import TemplateView

# Import feeds
import core.views
from events.feeds import EventFeed, feedview
import events.reports
import events.views
from ligoauth.views import pre_login, post_login, shib_logout, manage_password
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
    url(r'^alerts/', include('alerts.urls')),
    url(r'^feeds/(?P<url>.*)/$', EventFeed()),
    url(r'^feeds/$', feedview, name="feeds"),

    url(r'^performance/$', events.views.performance, name="performance"),
    url(r'^reports/$', events.reports.histo, name="reports"),
    url(r'^reports/cbc_report/(?P<format>(json|flex))?$',
        events.reports.cbc_report, name="cbc_report"),
    url(r'^latest/$', search.views.latest, name="latest"),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),
    url(r'^search/$', search.views.search, name="mainsearch"),

    # Authentication
    url(r'^login/$', pre_login, name='login'),
    url(r'^post-login/$', post_login, name='post-login'),
    url(r'^logout/$', shib_logout, name='logout'),

    # Password management
    url('^manage-password/$', manage_password, name='manage-password'),

    # API URLs
    url(r'^api/', include('api.urls')),
    # Legacy API URLs - must be maintained!
    url(r'^apibasic/', include('api.urls', namespace='legacy_apibasic')),
    url(r'^apiweb/', include('api.urls', namespace='legacy_apiweb')),

    # Heartbeat URL
    url(r'^heartbeat/$', core.views.heartbeat, name='heartbeat'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),

    # sessions
    #url(r'', include('user_sessions.urls', 'user_sessions')),

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
