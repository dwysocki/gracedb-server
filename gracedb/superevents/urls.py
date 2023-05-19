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

    # File list (file detail/download is handled through the API)
    url(r'^files/$', views.SupereventFileList.as_view(), name="file-list"),
]

# Legacy URL patterns - don't really need them, but we use them for the
# convenience of users who may be accustomed to the legacy event URL patterns

# public page url patterns. This needs to go first so django matches 
# the 'public' string before parsing it interprets it as a superevent_id.
# Note to future generations: don't name a GW 'public' or the link breaks.

public_urlpatterns = [
    # View of all public candidates
    path('public/', views.SupereventPublic.as_view(),
        name="public-alerts"),

    # redirect to the main public page. TODO: do something with the
    # integer? like jump to a specific table on the page? maybe have
    # a pull-down menu from the "Public Alerts" link that jumps to a
    # specific observation run?
     path('public/<slug:obsrun>/', views.public_alerts_redirect,
         name="public-alerts-redirect"),

]
legacy_urlpatterns = public_urlpatterns + [
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

]
