import logging

from django.urls import resolve
from rest_framework.settings import api_settings
from rest_framework.reverse import reverse as drf_reverse

from core.urls import build_absolute_uri

# Set up logger
logger = logging.getLogger(__name__)

# some default values
AUTH_NAMESPACES = ['api', 'x509', 'shib', 'basic']
DEFAULT_AUTH_NAMESPACE = 'api'


def api_reverse(viewname, args=None, kwargs=None, request=None, format=None,
    **extra):
    """
    Reverse which handles different API auth schemes and versions. If a
    request is provided, we want to send back URLs which use the same
    auth type and version as the user was using. If not, we send back
    the "default" auth scheme (currently 'x509') and version ('default').

    Standard usage:
        api_reverse('events:event-list', request=request)
        api_reverse('events:event-list')

    Not sure if we would ever *want* to specify the auth and version
    namespaces manually when a request is not provided, but if so, we
    can. The following are OK, too:
        api_reverse('default:events:event-list')
        api_reverse('v1:events:event-list')
        api_reverse('api:default:events:event-list')
        api_reverse('api:v1:events:event-list')
        api_reverse('x509:default:events:event-list')
        api_reverse('x509:v1:events:event-list')
    """
    namespaces = []
    if request:
        resolver_match = resolve(request.path)

        # We have to be careful here because this function is sometimes used
        # for requests whose path is not in the API.  I.e., when web views
        # try to serialize stuff (like EventLogToDict). The 'else' statement
        # handles that case
        if resolver_match.namespaces:
            # We only add the *first* namespace because it specifies the auth
            # namespace.  The version namespace will be handled by the
            # versioning class in this case.
            namespaces.append(resolver_match.namespaces[0])
        else:
            namespaces.append(DEFAULT_AUTH_NAMESPACE)
            namespaces.append(api_settings.DEFAULT_VERSION)
    else:
        # Otherwise, we check the viewname and add in the auth and version
        # namespaces as needed. Note that we have to add version namespaces (if
        # the code doesn't specify them) because there is no request, so
        # drf_reverse won't trigger the versioning class.

        # Split provided viewname to determine possible namespaces that are
        # already included
        possible_namespaces = viewname.split(':')[:-1]

        # Check if any auth namespaces were provided already; if not,
        # set to default using app_name
        if not any([v in possible_namespaces for v in AUTH_NAMESPACES]):
            namespaces.append(DEFAULT_AUTH_NAMESPACE)

        # Check if any version namespaces were provided already; if not,
        # set to default
        if not any([v in possible_namespaces for v in
            api_settings.ALLOWED_VERSIONS]):
            namespaces.append(api_settings.DEFAULT_VERSION)

    # Join namespaces to viewname    
    viewname = ':'.join(namespaces + [viewname])

    # Use rest_framework reverse to get url
    url = drf_reverse(viewname, args, kwargs, request, format, **extra)

    # Use sites to build absolute url if request is not available
    if request is None:
        url = build_absolute_uri(url)
   
    return url 
