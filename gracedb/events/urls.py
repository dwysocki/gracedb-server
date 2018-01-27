
# Changed for Django 1.11
from django.conf.urls import url

# Import views
from . import views
#import django.views.generic.list_detail

from .api.views import download

urlpatterns = [
    url(r'^$', views.index, name="home-events"),
    url(r'^create/$', views.create, name="create"),
    url(r'^search/(?P<format>(json|flex))?$', views.search, name="search"),
    url(r'^view/(?P<graceid>[GEHMT]\d+)', views.view, name="view"),
    url(r'^voevent/(?P<graceid>[GEHMT]\d+)', views.voevent, name="voevent"),
    #url (r'^skyalert/(?P<graceid>[GEHMT]\d+)', 'skyalert', name="skyalert"),
    url((r'^neighbors/(?P<graceid>[GEHMT]\d+)/\(?(?P<delta1>[-+]?\d+)'
         '(,(?P<delta2>[-+]?\d+)\)?)?'), views.neighbors, name="neighbors"),
    url(r'^(?P<graceid>[GEHMT]\d+)$', views.view, name="view2"),
    url(r'^(?P<graceid>[GEHMT]\d+)/t90/$', views.modify_t90,
        name="modify_t90"),
    url(r'^(?P<graceid>[GEHMT]\d+)/perms/$', views.modify_permissions,
        name="modify_permissions"),
    url(r'^(?P<graceid>[GEHMT]\d+)/signoff/$', views.modify_signoff,
        name="modify_signoff"),
    url(r'^(?P<graceid>[GEHMT]\d+)/files/$', views.file_list,
        name="file_list"),
    url(r'^(?P<graceid>[GEHMT]\d+)/files/(?P<filename>.*)$', download,
        name="file"),
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<num>([\d]*|preview))$',
        views.logentry, name="logentry"),
    url(r'^(?P<graceid>[GEHMT]\d+)/embblog/(?P<num>([\d]*|preview))$',
        views.embblogentry, name="embblogentry"),
    url(r'^(?P<graceid>[GEHMT]\d+)/emobservation/(?P<num>([\d]*|preview))$',
        views.emobservation_entry, name="emobservation_entry"),
    url(r'^(?P<graceid>[GEHMT]\d+)/log/(?P<num>\d+)/tag/(?P<tagname>.*)$',
        views.taglogentry, name="taglogentry"),

]
