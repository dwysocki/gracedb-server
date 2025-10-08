from django.urls import re_path

# Import views
from . import views


urlpatterns = [
    # Actual web views --------------------------------------------------------
    # Main site home page
    re_path(r'^$', views.index, name="home-events"),

    # Event creation page
    re_path(r'^create/$', views.create, name="create"),

    # Event detail page
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/view/$', views.view, name="view"),

    # Event file list and file download
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/files/$', views.file_list,
        name="file_list"),
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/files/(?P<filename>.*)$',
        views.file_download, name="file-download"),

    # Neighbors
    re_path((r'^(?P<graceid>[GEHMTD]\d+)/neighbors/\(?(?P<delta1>[-+]?\d+)'
         r'(,(?P<delta2>[-+]?\d+)\)?)?/$'), views.neighbors, name="neighbors"),

    # Form processing ---------------------------------------------------------
    # Modify permissions
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/perms/$', views.modify_permissions,
        name="modify_permissions"),
    # Modify signoffs
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/signoff/$', views.modify_signoff,
        name="modify_signoff"),
    # Create log entry
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/log/(?P<num>([\d]*|preview))$',
        views.logentry, name="logentry"),
    # Add tag to log
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/log/(?P<num>\d+)/tag/(?P<tagname>.*)$',
        views.taglogentry, name="taglogentry"),
    # Process EMObservation
    re_path(r'^(?P<graceid>[GEHMTD]\d+)/emobservation/(?P<num>([\d]*|preview))$',
        views.emobservation_entry, name="emobservation_entry"),

    # Manage pipelines
    re_path(r'^pipelines/manage/$', views.PipelineManageView.as_view(),
        name='manage-pipelines'),
    re_path(r'^pipelines/(?P<pk>\d+)/enable/$', views.PipelineEnableView.as_view(),
        name='enable-pipeline'),
    re_path(r'^pipelines/(?P<pk>\d+)/disable/$',
        views.PipelineDisableView.as_view(), name='disable-pipeline'),

    # Legacy URLs -------------------------------------------------------------
    # Event detail
    re_path(r'^view/(?P<graceid>[GEHMTD]\d+)', views.view, name="legacyview"),
    re_path(r'^(?P<graceid>[GEHMTD]\d+)$', views.view, name="legacyview2"),

    # Neighbors
    re_path((r'^neighbors/(?P<graceid>[GEHMTD]\d+)/\(?(?P<delta1>[-+]?\d+)'
         r'(,(?P<delta2>[-+]?\d+)\)?)?'), views.neighbors,
        name="legacyneighbors"),
]
