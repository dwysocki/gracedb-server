
# Changed for Django 1.6
#from django.conf.urls.defaults import *
from django.conf.urls import patterns, url, include


urlpatterns = patterns('userprofile.views',
    url (r'^$', 'index', name="userprofile-home"),
    url (r'^contact/create$', 'createContact', name="userprofile-create-contact"),
    url (r'^contact/delete/(?P<id>[\d]+)$', 'deleteContact', name="userprofile-delete-contact"),
    url (r'^contact/edit/(?P<id>[\d]+)$', 'editContact', name="userprofile-edit-contact"),

    url (r'^trigger/create$', 'create', name="userprofile-create"),
    url (r'^trigger/delete/(?P<id>[\d]+)$', 'delete', name="userprofile-delete"),
    url (r'^trigger/edit/(?P<id>[\d]+)$', 'edit', name="userprofile-edit"),

#   (r'^view/(?P<uid>[\w\d]+)', 'view'),
#   (r'^edit/(?P<uid>[\w\d]+)', 'edit'),
#   (r'^request_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'request_archive'),
#   (r'^approve_archive/(?P<uid>[\w\d]+)(?P<rescind>/rescind)?', 'approve_archive'),
#   url (r'^query', 'query', name="search"),
#   url (r'^mine/$', 'mine', name="mine"),
#   url (r'^myapprovals/$', 'myapprovals', name="myapprovals"),
)
