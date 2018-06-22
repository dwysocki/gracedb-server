from django.conf.urls import url, include
from .models import Superevent
from . import views

app_name = 'superevents'

# URLs which are nested below a superevent detail
# These are included under a superevent's ID URL prefix (see below)
suburlpatterns = [

    # Superevent detail view
    url(r'^view/$', views.SupereventDetailView.as_view(), name="view"),
    #url(r'^(?P<superevent_id>{regex})/oldview/$'.format(
    #    regex=Superevent.ID_REGEX), views.old_webview, name="oldview"),
    #url(r'^(?P<superevent_id>{regex})/create_log/$'.format(
    #    regex=Superevent.ID_REGEX), views.web_create_log, name="create-log"),

    # Confirm as GW
    url(r'^confirm_as_gw/$', views.confirm_as_gw, name="confirm-gw"),

    # Files
    url(r'^files/$', views.file_list, name="file-list"),
    url(r'^files/(?P<filename>.*)$', views.file_download, name="file-download"),

    # Changing LV-EM observers' superevent view/change permissions
    url(r'^perms/$', views.modify_permissions, name="modify-permissions"),

    # Signoff updates
    url(r'^signoff/$', views.modify_signoff, name="modify-signoff"),
]

# Legacy URL patterns
legacy_urlpatterns = [
    # Legacy URLs for superevent detail view
    url(r'^(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(), name="legacyview1"),
    url(r'^view/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(), name="legacyview2"),
]

# Full urlpatterns: legacy urls plus suburlpatterns nested under
# superevent_id
urlpatterns = legacy_urlpatterns + [
    url(r'^(?P<superevent_id>{regex})/'.format(regex=Superevent.ID_REGEX),
        include(suburlpatterns)),
]
