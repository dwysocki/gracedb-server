"""
v2 search filter for the Superevent list endpoint.

Accepts a structured JSON or YAML query body (or a ``query`` URL parameter
containing a JSON string) and translates it to Django ORM operations via the
v2 translator.

Content-Type negotiation:
  - ``application/json`` (or no Content-Type on GET): parse body/param as JSON.
  - ``application/yaml`` / ``application/x-yaml`` / ``text/yaml``: parse as
    YAML using ``yaml.safe_load`` (never ``yaml.load``, to prevent code
    execution from user-supplied YAML).
  - When both a request body and a ``query`` URL parameter are present, the
    body takes precedence.

Error responses always have the shape::

    {
        "error": "invalid_query",
        "message": "<human-readable description>",
        "path":    "<dot-path to the offending node, or null>",
        "version": "2"
    }
"""
import json
import logging

import yaml
from rest_framework import filters, exceptions, status

from search.query.v2.translator import inject_default_filter, apply_query
from search.query.v2.validator import validate, QueryValidationError
from .paginators import CustomSupereventPagination
from ...v1.superevents.filters import SupereventOrderingFilter  # re-export unchanged

logger = logging.getLogger(__name__)

_YAML_CONTENT_TYPES = {'application/yaml', 'application/x-yaml', 'text/yaml'}


class V2SearchError(exceptions.APIException):
    """
    A v2 structured query error.

    Unlike ``ParseError``, the ``detail`` attribute is NOT a dict — it is a
    plain string key.  This prevents the GraceDB custom exception handler
    (``gracedb_exception_handler``) from iterating over the dict values and
    flattening them into a list of characters.

    The structured payload is stored in ``structured_payload`` and injected
    into the response by the custom exception handler override in the v2
    views.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'invalid_query'

    def __init__(self, message, path=None):
        self.structured_payload = {
            'error': 'invalid_query',
            'message': message,
            'path': path,
            'version': '2',
        }
        # Use a plain string detail so the GraceDB custom handler skips it.
        super().__init__(detail='invalid_query')


def _parse_body(request):
    """
    Extract and deserialise the query from *request*.

    Returns a Python dict on success, raises ``V2SearchError`` on failure.

    Precedence: request body > ``query`` URL parameter.
    """
    content_type = request.content_type or ''
    use_yaml = any(ct in content_type for ct in _YAML_CONTENT_TYPES)

    # Prefer body; fall back to URL parameter.  Note: for standard GET list
    # requests the body will be empty and we fall through to the query param.
    raw = None
    try:
        body_bytes = request.body
    except Exception:
        body_bytes = b''
    if body_bytes:
        try:
            raw = body_bytes.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            pass

    if raw is None:
        raw = request.query_params.get('query')

    if not raw:
        return None  # No query supplied — caller returns unfiltered queryset.

    try:
        if use_yaml:
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise V2SearchError(f'Could not parse query body: {exc}')

    if not isinstance(data, dict):
        raise V2SearchError('Query body must be a JSON/YAML object.')

    return data


class V2SupereventSearchFilter(filters.BaseFilterBackend):
    """
    DRF filter backend that applies a v2 structured query to the Superevent
    queryset.

    Raises ``V2SearchError`` (a custom ``APIException`` subclass) on any query
    error.  The ``SupereventViewSet.handle_exception`` override converts this
    to a structured JSON 400 response.
    """

    def filter_queryset(self, request, queryset, view):
        data = _parse_body(request)

        if data is None:
            return queryset

        # Optional: validate that the query targets the right object type.
        declared_type = data.get('object_type')
        if declared_type is not None and declared_type != 'superevent':
            raise V2SearchError(
                f"object_type '{declared_type}' does not match this "
                "endpoint (expected 'superevent').",
                path='object_type',
            )

        query_node = data.get('query', data)

        # Semantic validation (strict mode — raises QueryValidationError).
        try:
            validate(query_node, 'superevent', strict=True)
        except QueryValidationError as exc:
            raise V2SearchError(str(exc), path=exc.path)

        # Inject the default category filter unless the query already
        # references category/id fields.
        query_node = inject_default_filter(query_node, 'superevent')

        from superevents.models import Superevent
        try:
            filtered_qs = apply_query(Superevent, query_node, 'superevent')
        except Exception as exc:
            logger.exception('v2 superevent query execution failed')
            raise V2SearchError(f'Query execution failed: {exc}')

        # Intersect with the already-permission-filtered queryset so that
        # object-level permissions applied earlier are preserved.
        return queryset.filter(pk__in=filtered_qs.values('pk'))
