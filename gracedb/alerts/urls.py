from django.conf.urls import url

from . import views

app_name = 'alerts'


urlpatterns = [
    # Base /options/ URL
    url(r'^$', views.index, name="index"),

    # Contacts
    url(r'^contact/create/', views.CreateContactView.as_view(),
        name='create-contact'),
    url(r'^contact/(?P<pk>\d+)/edit/$', views.EditContactView.as_view(),
        name="edit-contact"),
    url(r'^contact/(?P<pk>\d+)/delete/$', views.DeleteContactView.as_view(),
        name="delete-contact"),
    url(r'^contact/(?P<pk>\d+)/test/$', views.TestContactView.as_view(),
        name="test-contact"),
    url(r'^contact/(?P<pk>\d+)/request-code/$',
        views.RequestVerificationCodeView.as_view(),
        name="request-verification-code"),
    url(r'^contact/(?P<pk>\d+)/verify/$', views.VerifyContactView.as_view(),
        name="verify-contact"),

    # Notifications
    url(r'^notification/create/$', views.create, name="create-notification"),
    url(r'^notification/delete/(?P<id>[\d]+)$', views.delete,
        name="delete-notification"),
    #url(r'^notification/edit/(?P<id>[\d]+)$', views.edit,
    #    name="edit-notification"),

    # Manage password
    url(r'^manage_password/$', views.managePassword,
        name="manage-password"),

]
