
# Changed for Django 1.11
from django.conf.urls import url
from . import views

urlpatterns = [
    # Base /options/ URL
    url(r'^$', views.index, name="userprofile-home"),

    # /options/contact/
    url(r'^contact/create$', views.createContact,
        name="userprofile-create-contact"),
    url(r'^contact/delete/(?P<id>[\d]+)$', views.deleteContact,
        name="userprofile-delete-contact"),
    url(r'^contact/test/(?P<id>[\d]+)$', views.testContact,
        name="userprofile-test-contact"),
    #url(r'^contact/edit/(?P<id>[\d]+)$', views.editContact,
    #    name="userprofile-edit-contact"),

    # /options/trigger/
    url(r'^trigger/create$', views.create, name="userprofile-create"),
    url(r'^trigger/delete/(?P<id>[\d]+)$', views.delete,
        name="userprofile-delete"),
    #url(r'^trigger/edit/(?P<id>[\d]+)$', views.edit, name="userprofile-edit"),

    # /options/manage_password
    url(r'^manage_password$', views.managePassword,
        name="userprofile-manage-password"),

]
