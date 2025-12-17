# URL utilities

from django.conf import settings
from django.contrib.sites.models import Site


def build_absolute_uri(relative_uri, request=None):
    if request is not None:
        return request.build_absolute_uri(relative_uri)
    else:
        # Assume HTTPS
        domain = Site.objects.get_current().domain
        protocol = 'https'
        if getattr(settings, 'USE_HTTP', False):
            protocol = 'http'
            port = getattr(settings, 'HTTP_PORT', None)
            if port:
                domain += ':' + port
        return protocol + '://' + domain + relative_uri


# A helper function to return superevent urls from /api/-->/apiweb/
# Note that event files are never exposed to the public and so aren't 
# subject to the same private api vs public apiweb caching schemes
def build_apiweb_uri(relative_uri, request=None):
    absolute_uri = build_absolute_uri(relative_uri, request=request)

    # Return the apiweb url for superevents:
    if '/superevents/' in absolute_uri:
        absolute_uri = absolute_uri.replace('/api/', '/apiweb/')

    return absolute_uri

