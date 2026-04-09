"""
v2 search filter helpers for the Event list endpoint.

The event list is an APIView (not a ViewSet), so there is no DRF
``filter_backends`` slot.  Instead, this module exposes a single function
``apply_v2_event_filter`` that the v2 EventList view calls directly.

Parsing and error-handling follow the same conventions as the superevent
filter (see ``gracedb/api/v2/superevents/filters.py``).
"""
import json
import logging

import yaml
from rest_framework import exceptions, status

from search.query.v2.translator import inject_default_filter, apply_query
from search.query.v2.validator import validate, QueryValidationError

logger = logging.getLogger(__name__)

_YAML_CONTENT_TYPES = {'application/yaml', 'application/x-yaml', 'text/yaml'}


class V2EventSearchError(exceptions.APIException):
    """
    Structured v2 search error for the events endpoint.

    Uses a plain-string ``detail`` so the GraceDB custom exception handler
    (``gracedb_exception_handler``) doesn't flatten the structured payload
    into individual characters.
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
        super().__init__(detail='invalid_query')


def _parse_body(request):
    """
    Extract and deserialise the query from *request*.

    Returns a Python dict on success, ``None`` if no query was supplied, or
    raises ``exceptions.ParseError`` with a structured payload on failure.

    Precedence: request body > ``query`` URL parameter.
    """
    content_type = request.content_type or ''
    use_yaml = any(ct in content_type for ct in _YAML_CONTENT_TYPES)

    raw = None
    if request.body:
        try:
            raw = request.body.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            pass

    if raw is None:
        raw = request.query_params.get('query')

    if not raw:
        return None

    try:
        if use_yaml:
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise V2EventSearchError(f'Could not parse query body: {exc}')

    if not isinstance(data, dict):
        raise V2EventSearchError('Query body must be a JSON/YAML object.')

    return data


def apply_v2_event_filter(request, base_queryset):
    """
    Parse, validate, and execute a v2 query against *base_queryset*.

    Args:
        request:        DRF Request object.
        base_queryset:  A queryset of ``Event`` objects (already
                        permission-filtered by the caller).

    Returns:
        A (possibly filtered) queryset, or the original *base_queryset* if no
        query was supplied.

    Raises:
        ``V2EventSearchError`` for any query error (parse failure, validation
        error, or execution error).
    """
    data = _parse_body(request)

    if data is None:
        return base_queryset

    declared_type = data.get('object_type')
    if declared_type is not None and declared_type != 'event':
        raise V2EventSearchError(
            f"object_type '{declared_type}' does not match this "
            "endpoint (expected 'event').",
            path='object_type',
        )

    query_node = data.get('query', data)

    try:
        validate(query_node, 'event', strict=True)
    except QueryValidationError as exc:
        raise V2EventSearchError(str(exc), path=exc.path)

    query_node = inject_default_filter(query_node, 'event')

    from events.models import Event
    try:
        filtered_qs = apply_query(Event, query_node, 'event')
    except Exception as exc:
        logger.exception('v2 event query execution failed')
        raise V2EventSearchError(f'Query execution failed: {exc}')

    # Intersect with the caller-supplied (permission-filtered) queryset.
    return base_queryset.filter(pk__in=filtered_qs.values('pk'))
