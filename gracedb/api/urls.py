from django.conf.urls import url, include
# Test to disable caching on the /api/ part of the site. 
# From django-snippets:
# https://djangosnippets.org/snippets/355/ 

from django.views.decorators.cache import never_cache
from .v1 import urls as v1_urls
from .v2 import urls as v2_urls

app_name = 'api'


def never_cache_patterns(prefix, *args):
    pattern_list = [], tterns,
    for t in args:
        if isinstance(t, (list, tuple)): 
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)
    
        t._callback = never_cache(t.callback)
        pattern_list.append(t)

    return pattern_list


urlpatterns = [
    url(r'^', include((never_cache(v1_urls), 'default'))),
    url(r'^v1/', include((never_cache(v1_urls), 'v1'))),
    url(r'^v2/', include((never_cache(v2_urls), 'v2'))),
]

#urlpatterns = [
#    url(r'^', include((v1_urls, 'default'))),
#    url(r'^v1/', include((v1_urls, 'v1'))),
#    url(r'^v2/', include((v2_urls, 'v2'))),
#]
