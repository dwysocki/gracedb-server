import hashlib
import logging

from django.urls import resolve, reverse as django_reverse
from rest_framework.settings import api_settings
from rest_framework.response import Response

from core.urls import build_absolute_uri

# Set up logger
logger = logging.getLogger(__name__)


def get_count_cache_key(request, prefix, limit_query_param='count',
                        offset_query_param='start'):
    """
    Generate a cache key for paginated count queries, unique to user + query.

    Args:
        request: The HTTP request object
        prefix: A string prefix to distinguish cache types (e.g., 'event', 'superevent')
        limit_query_param: The query parameter name for limit (excluded from hash)
        offset_query_param: The query parameter name for offset (excluded from hash)

    Returns:
        A cache key string in the format '{prefix}_count:{user_id}:{query_hash}'
    """
    user_id = request.user.id if request.user.is_authenticated else 'AnonymousUser'
    # Use the query string (includes search params but not start/count)
    # Strip out pagination params so page 1 and page 2 share the cache
    query_params = request.query_params.copy()
    query_params.pop(limit_query_param, None)
    query_params.pop(offset_query_param, None)
    query_string = query_params.urlencode()
    query_hash = hashlib.md5(query_string.encode()).hexdigest()
    return f'{prefix}_count:{user_id}:{query_hash}'

# Some default values
API_NAMESPACE = 'api'


def api_reverse(viewname, args=None, kwargs=None, request=None, format=None,
    absolute_path=True, **extra):
    """
    Usage:
        # No request and no version in viewname uses default version
        # Same for case when request points to a non-API url
        api_reverse('api:events:event-list')
        api_reverse('events:event-list')
        api_reverse('api:events:event-list', request=request)
        api_reverse('events:event-list', request=request)
            /api/events/

        # No request but with version in viewname uses the specified version
        # Same for case when request points to a non-API url
        api_reverse('api:v1:events:event-list')
        api_reverse('api:v1:events:event-list', request=request)
            /api/v1/events/
        api_reverse('v2:events:event-list')
        api_reverse('v2:events:event-list', request=request)
            /api/v2/events/

        # Request pointing to an API URL uses the specified version in the
        # viewname. If a version is not specified in the viewname, the version
        # is determined from the request.
        api_reverse('api:v1:events:event-list, request=request)
        api_reverse('v1:events:event-list, request=request)
            /api/v1/events/ (request.path is like /api/(any version)/*)

        api_reverse('api:events:event-list, request=request)
        api_reverse('events:event-list, request=request)
            /api/v2/events (request.path is like /api/v2/*)
    """

    # Prepend 'api:' if viewname doesn't start with it.
    if not viewname.startswith(API_NAMESPACE + ':'):
        viewname = API_NAMESPACE + ':' + viewname

    # Handle versioning. Nothing is done by the versioning_class if the
    # viewname already has a version namespace.
    versioning_class = api_settings.DEFAULT_VERSIONING_CLASS()
    viewname = versioning_class.get_versioned_viewname(viewname, request)

    # Get URL
    url = django_reverse(viewname, args=args, kwargs=kwargs, **extra)
    if absolute_path:
        url = build_absolute_uri(url)

    return url


def is_api_request(request_path):
    """
    Returns True/False based on whether the request is directed to the API
    """

    # This is hard-coded because things break if we try to import it from .urls
    api_app_name = 'api'

    resolver_match = resolve(request_path)
    if (resolver_match.app_names and
        resolver_match.app_names[0] == api_app_name):
        return True
    return False

class ResponseThenRun(Response):
    """
    A response class that will do something after the response is sent
    """
    def __init__(self, data, callback, callback_kwargs, **kwargs):
       super(ResponseThenRun, self).__init__(data, **kwargs)
       self.callback = callback
       self.callback_kwargs = callback_kwargs

    def close(self):
        super().close()
        self.callback(**self.callback_kwargs)
