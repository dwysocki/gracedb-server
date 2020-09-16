from django.conf.urls import url, include
from django.urls import path
from .models import Superevent
from . import views

app_name = 'superevents'


# URLs which are nested below a superevent detail
# These are included under a superevent's ID URL prefix (see below)
suburlpatterns = [

    # Superevent detail view
    url(r'^view/$', views.SupereventDetailView.as_view(), name="view"),

    # Superevent catalog view
    url(r'^catalog/$', views.SupereventDetailCuratedView.as_view(), name="catalog"),

    # File list (file detail/download is handled through the API)
    url(r'^files/$', views.SupereventFileList.as_view(), name="file-list"),
]

# Legacy URL patterns - don't really need them, but we use them for the
# convenience of users who may be accustomed to the legacy event URL patterns
legacy_urlpatterns = [
    # Legacy URLs for superevent detail view
    path('<str:superevent_id>/',
        views.SupereventDetailView.as_view(),
        name="legacyview1"),
    path('view/<str:superevent_id>/',
        views.SupereventDetailView.as_view(),
        name="legacyview2"),
]

# Full urlpatterns: legacy urls plus suburlpatterns nested under
# superevent_id
urlpatterns = legacy_urlpatterns + [
    path('<str:superevent_id>/',
        include(suburlpatterns)),

    # View of all candidates
    path('public/O3/', views.SupereventPublic.as_view(),
        name="public-alerts-O3"),

    path('catalog/O3/', views.SupereventCurated.as_view(),
        name="curated-events-O3"),

]
