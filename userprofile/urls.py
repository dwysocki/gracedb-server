
# Changed for Django 1.6
#from django.conf.urls.defaults import *
from django.conf.urls import patterns, url

urlpatterns = patterns('userprofile.views',
    # Base /options/ URL
    url(r'^$', 'index', name="userprofile-home"),

    # /options/contact/
    url(r'^contact/create$', 'createContact',
        name="userprofile-create-contact"),
    url(r'^contact/delete/(?P<id>[\d]+)$', 'deleteContact',
        name="userprofile-delete-contact"),
    url(r'^contact/test/(?P<id>[\d]+)$', 'testContact',
        name="userprofile-test-contact"),
    url(r'^contact/edit/(?P<id>[\d]+)$', 'editContact',
        name="userprofile-edit-contact"),

    # /options/trigger/
    url(r'^trigger/create$', 'create', name="userprofile-create"),
    url(r'^trigger/delete/(?P<id>[\d]+)$', 'delete',
        name="userprofile-delete"),
    url(r'^trigger/edit/(?P<id>[\d]+)$', 'edit', name="userprofile-edit"),

    # /options/manage_password
    url(r'^manage_password$', 'managePassword',
        name="userprofile-manage-password"),

)
