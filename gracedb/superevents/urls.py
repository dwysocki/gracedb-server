from django.conf.urls import url
from .models import Superevent
from . import views

app_name = 'superevents'

urlpatterns = [
    #url(r'^$', views.index, name="index"),
    #url(r'^create/$', views.create, name="create"),
    #url(r'^search/(?P<format>(json|flex))?$', views.search, name="search"),
    url(r'^view/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.webview, name="view"),
    url(r'^create_log/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.web_create_log, name="create-log"),

    # Files
    url(r'^(?P<superevent_id>{regex})/files/$'.format(
        regex=Superevent.ID_REGEX), views.file_list, name="file-list"),
    url(r'^(?P<superevent_id>{regex})/files/(?P<filename>.*)$'.format(
        regex=Superevent.ID_REGEX), views.file_download, name="file-download"),
]
