from django.urls import re_path, include
from .models import Superevent
from . import views

app_name = 'superevents'


# URLs which are nested below a superevent detail
# These are included under a superevent's ID URL prefix (see below)
suburlpatterns = [

    # Superevent detail view
    re_path(r'^view/$', views.SupereventDetailView.as_view(), name="view"),

    # File list (file detail/download is handled through the API)
    re_path(r'^files/$', views.SupereventFileList.as_view(), name="file-list"),
]

# Legacy URL patterns - don't really need them, but we use them for the
# convenience of users who may be accustomed to the legacy event URL patterns
legacy_urlpatterns = [
    # Legacy URLs for superevent detail view
    re_path(r'^(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(),
        name="legacyview1"),
    re_path(r'^view/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(),
        name="legacyview2"),
]

# Full urlpatterns: legacy urls plus suburlpatterns nested under
# superevent_id
urlpatterns = legacy_urlpatterns + [
    re_path(r'^(?P<superevent_id>{regex})/'.format(regex=Superevent.ID_REGEX),
        include(suburlpatterns)),

    # View of all candidates
    re_path(r'^public/O3/$', views.SupereventPublic.as_view(),
        name="public-alerts-O3"),
]
