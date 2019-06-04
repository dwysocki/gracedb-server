from django.conf.urls import url, include
from .models import Superevent
from . import views

app_name = 'superevents'


# URLs which are nested below a superevent detail
# These are included under a superevent's ID URL prefix (see below)
suburlpatterns = [

    # Superevent detail view
    url(r'^view/$', views.SupereventDetailView.as_view(), name="view"),

    # File list (file detail/download is handled through the API)
    url(r'^files/$', views.SupereventFileList.as_view(), name="file-list"),
]

# Legacy URL patterns - don't really need them, but we use them for the
# convenience of users who may be accustomed to the legacy event URL patterns
legacy_urlpatterns = [
    # Legacy URLs for superevent detail view
    url(r'^(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(),
        name="legacyview1"),
    url(r'^view/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.SupereventDetailView.as_view(),
        name="legacyview2"),
]

# Full urlpatterns: legacy urls plus suburlpatterns nested under
# superevent_id
urlpatterns = legacy_urlpatterns + [
    url(r'^(?P<superevent_id>{regex})/'.format(regex=Superevent.ID_REGEX),
        include(suburlpatterns)),

    # View of all candidates
    url(r'^public/$', views.SupereventPublic.as_view(), name="public-alerts"),
]
