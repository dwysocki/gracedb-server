from django.urls import re_path

from . import views

app_name = 'alerts'


urlpatterns = [
    # Base /options/ URL
    re_path(r'^$', views.index, name="index"),

    # Contacts
    re_path(r'^contact/create/', views.CreateContactView.as_view(),
        name='create-contact'),
    re_path(r'^contact/(?P<pk>\d+)/edit/$', views.EditContactView.as_view(),
        name="edit-contact"),
    re_path(r'^contact/(?P<pk>\d+)/delete/$', views.DeleteContactView.as_view(),
        name="delete-contact"),
    re_path(r'^contact/(?P<pk>\d+)/test/$', views.TestContactView.as_view(),
        name="test-contact"),
    re_path(r'^contact/(?P<pk>\d+)/request-code/$',
        views.RequestVerificationCodeView.as_view(),
        name="request-verification-code"),
    re_path(r'^contact/(?P<pk>\d+)/verify/$', views.VerifyContactView.as_view(),
        name="verify-contact"),

    # Notifications
    re_path(r'^notification/create/$', views.CreateNotificationView.as_view(),
        name="create-notification"),
    re_path(r'^notification/(?P<pk>\d+)/edit/$',
        views.EditNotificationView.as_view(), name="edit-notification"),
    re_path(r'^notification/(?P<pk>\d+)/delete/$',
        views.DeleteNotificationView.as_view(), name="delete-notification"),
]
