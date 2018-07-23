from django.conf.urls import url, include

app_name = 'api'

urlpatterns = [
    url(r'^', include('api.v1.urls', namespace='default')),
    url(r'^v1/', include('api.v1.urls', namespace='v1')),
    #url(r'^v2/', include('api.v2.urls', namespace='v2')),
]
