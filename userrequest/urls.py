
from django.conf.urls import patterns, url

urlpatterns = patterns('userrequest.views',
    url (r'^$', 'index', name="userrequest-home"),

    #url (r'^robotcert/create$', 'createRequest', name="userrequest-create-request"),

)
