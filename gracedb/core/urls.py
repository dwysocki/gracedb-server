# URL utilities

from django.contrib.sites.models import Site

def build_absolute_uri(relative_uri, request=None):
    if request is not None:
        return request.build_absolute_uri(relative_uri)
    else:
        # Assume HTTPS
        domain = Site.objects.get_current().domain
        return 'https://' + domain + relative_uri
