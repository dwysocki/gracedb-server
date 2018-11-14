from django.conf.urls import url

# Import views
from . import views


urlpatterns = [
    # Actual web views --------------------------------------------------------
    # Main site home page
    url(r'^$', views.index, name="home-events"),

    # Event creation page
    url(r'^create/$', views.create, name="create"),

    # Event detail page
    url(r'^(?P<graceid>[GEHMT]\d+)/view/$', views.view, name="view"),

    # Event file list and file download
    url(r'^(?P<graceid>[GEHMT]\d+)/files/$', views.file_list,
        name="file_list"),
    url(r'^(?P<graceid>[GEHMT]\d+)/files/(?P<filename>.*)$',
        views.file_download, name="file-download"),

    # Neighbors
    url((r'^(?P<graceid>[GEHMT]\d+)/neighbors/\(?(?P<delta1>[-+]?\d+)'
         '(,(?P<delta2>[-+]?\d+)\)?)?/$'), views.neighbors, name="neighbors"),

    # Form processing ---------------------------------------------------------
    # Modify t90
    url(r'^(?P<graceid>[GEHMT]\d+)/t90/$', views.modify_t90,
        name="modify_t90"),
    # Modify permissions
    url(r'^(?P<graceid>[GEHMT]\d+)/perms/$', views.modify_permissions,
        name="modify_permissions"),
    # Modify signoffs
    url(r'^(?P<graceid>[GEHMT]\d+)/signoff/$', views.modify_signoff,
        name="modify_signoff"),
    # Create log entry
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<num>([\d]*|preview))$',
        views.logentry, name="logentry"),
    # Add tag to log
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<num>\d+)/tag/(?P<tagname>.*)$',
        views.taglogentry, name="taglogentry"),
    # Process EMBBEventLog
    url(r'^(?P<graceid>[GEHMT]\d+)/embblog/(?P<num>([\d]*|preview))$',
        views.embblogentry, name="embblogentry"),
    # Process EMObservation
    url(r'^(?P<graceid>[GEHMT]\d+)/emobservation/(?P<num>([\d]*|preview))$',
        views.emobservation_entry, name="emobservation_entry"),

    # Legacy URLs -------------------------------------------------------------
    # Event detail
    url(r'^view/(?P<graceid>[GEHMT]\d+)', views.view, name="legacyview"),
    url(r'^(?P<graceid>[GEHMT]\d+)$', views.view, name="legacyview2"),

    # Neighbors
    url((r'^neighbors/(?P<graceid>[GEHMT]\d+)/\(?(?P<delta1>[-+]?\d+)'
         '(,(?P<delta2>[-+]?\d+)\)?)?'), views.neighbors,
        name="legacyneighbors"),
]
