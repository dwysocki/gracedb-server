from django.conf.urls import url
from .models import Superevent
from . import views

app_name = 'superevents'

urlpatterns = [
    #url(r'^$', views.index, name="index"),
    #url(r'^create/$', views.create, name="create"),
    url(r'^(?P<superevent_id>{regex})/view/$'.format(
        regex=Superevent.ID_REGEX), views.webview, name="view"),
    url(r'^create_log/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.web_create_log, name="create-log"),
    url(r'^confirm_as_gw/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.confirm_as_gw, name="confirm-gw"),

    # Files
    url(r'^(?P<superevent_id>{regex})/files/$'.format(
        regex=Superevent.ID_REGEX), views.file_list, name="file-list"),
    url(r'^(?P<superevent_id>{regex})/files/(?P<filename>.*)$'.format(
        regex=Superevent.ID_REGEX), views.file_download, name="file-download"),

    # Legacy URLs for superevent detail view
    url(r'^(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.webview, name="legacyview1"),
    url(r'^view/(?P<superevent_id>{regex})/$'.format(
        regex=Superevent.ID_REGEX), views.webview, name="legacyview2"),

]
