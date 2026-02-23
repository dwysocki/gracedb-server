from django.conf import settings

from django.urls import re_path, include

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView

# Import feeds
import core.views
from events.feeds import EventFeed, feedview
import events.reports
import events.views
from ligoauth.views import (
    manage_password, ShibLoginView, ShibPostLoginView, PasswordLoginView
)
from ligoauth.debug_views import debug_shib_headers
import search.views

# Django admin auto-discover
admin.autodiscover()

feeds = {
    'latest' : EventFeed
}


urlpatterns = [
    re_path(r'^$', events.views.index, name="home"),
    re_path(r'^navbar_only$', TemplateView.as_view(
        template_name='navbar_only.html'), name="navbar-only"),
    re_path(r'^SPInfo', TemplateView.as_view(template_name='gracedb/spinfo.html'),
         name="spinfo"),
    re_path(r'^SPPrivacy', TemplateView.as_view(
        template_name='gracedb/spprivacy.html'), name="spprivacy"),
    re_path(r'^DiscoveryService', TemplateView.as_view(
        template_name='discovery.html'), name="discovery"),
    re_path(r'^events/', include('events.urls')),
    re_path(r'^superevents/', include('superevents.urls')),
    re_path(r'^alerts/', include('alerts.urls')),
    re_path(r'^feeds/(?P<url>.*)/$', EventFeed()),
    re_path(r'^feeds/$', feedview, name="feeds"),

    re_path(r'^other/$', TemplateView.as_view(template_name='other.html'),
        name='other'),
    re_path(r'^performance/$', events.views.performance, name="performance"),
    re_path(r'^reports/$', events.reports.reports_page_context, name="reports"),
    re_path(r'^latest/$', search.views.latest, name="latest"),
    #(r'^reports/(?P<path>.+)$', 'django.views.static.serve',
    #        {'document_root': settings.LATENCY_REPORT_DEST_DIR}),
    re_path(r'^search/$', search.views.search, name="mainsearch"),

    # Authentication
    re_path(r'^post-login/$', ShibPostLoginView.as_view(), name='post-login'),
    re_path(r'^logout/$', LogoutView.as_view(), name='logout'),

    # Password management
    re_path('^manage-password/$', manage_password, name='manage-password'),

    # API URLs
    re_path(r'^api/', include('api.urls')),
    # Legacy API URLs - must be maintained!
    re_path(r'^apibasic/', include('api.urls', namespace='legacy_apibasic')),
    re_path(r'^apiweb/', include('api.urls', namespace='legacy_apiweb')),

    # Heartbeat URL
    re_path(r'^heartbeat/$', core.views.heartbeat, name='heartbeat'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    re_path(r'^admin/', admin.site.urls),

    # Sessions
    re_path(r'^', include('user_sessions.urls', 'user_sessions')),

]

# Append the login view depending on the instance;
login_view = ShibLoginView
if not settings.USE_SHIBBOLETH_LOGIN:
    login_view = PasswordLoginView
urlpatterns.append(
    re_path(r'^login/$', login_view.as_view(), name='login')
)

# We don't require settings.DEBUG for django-silk since running unit tests
# by default sets settings.DEBUG to False, unless you use the
# --debug-mode flag
if ('silk' in settings.INSTALLED_APPS):
    # Add django-silk
    urlpatterns = [
        re_path(r'^silk/', include('silk.urls', namespace='silk'))
    ] + urlpatterns

# Add Shibboleth login debug view. DEBUG=False for playground
# and production instances
if settings.DEBUG and settings.USE_SHIBBOLETH_LOGIN:
    urlpatterns.append(re_path(r'^debug-shib/$', debug_shib_headers, name='debug-shib'),)

# Add django-debug-toolbar
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
