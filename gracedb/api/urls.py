from django.conf.urls import url, include

from .v1 import urls as v1_urls
from .v2 import urls as v2_urls

app_name = 'api'


urlpatterns = [
    url(r'^', include((v1_urls, 'default'))),
    url(r'^v1/', include((v1_urls, 'v1'))),
    url(r'^v2/', include((v2_urls, 'v2'))),
]
