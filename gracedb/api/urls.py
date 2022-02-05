from django.urls import re_path, include

from .v1 import urls as v1_urls
from .v2 import urls as v2_urls

app_name = 'api'

urlpatterns = [
    re_path(r'^', include((v1_urls, 'default'))),
    re_path(r'^v1/', include((v1_urls, 'v1'))),
    re_path(r'^v2/', include((v2_urls, 'v2'))),
]
