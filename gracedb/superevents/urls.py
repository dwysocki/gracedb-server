from django.conf.urls import url
from .models import Superevent
from . import views

app_name = 'superevents'

urlpatterns = [
    #url(r'^$', views.index, name="index"),
    #url(r'^create/$', views.create, name="create"),
    #url(r'^search/(?P<format>(json|flex))?$', views.search, name="search"),
    url(r'^view/(?P<superevent_id>{pref}\d+)$'.format(
        pref=Superevent.ID_PREFIX), views.webview, name="view"),
    url(r'^create_log/(?P<superevent_id>{pref}\d+)$'.format(
        pref=Superevent.ID_PREFIX), views.web_create_log, name="create-log"),
]
