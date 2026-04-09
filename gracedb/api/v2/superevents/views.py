"""
v2 superevent views.

Re-exports everything from v1, then overrides SupereventViewSet to:
  1. Swap in the v2 search filter (replaces the v1 text-based filter) for GET
     list requests.
  2. Add a ``search`` POST action that accepts a JSON/YAML query body and
     returns paginated results — without interfering with the ``create``
     action that also lives on POST to the list endpoint.

Usage::

    # GET with URL parameter (backwards-compatible with v1):
    GET /api/v2/superevents/?query=<json>

    # POST body (JSON or YAML):
    POST /api/v2/superevents/search/
    Content-Type: application/json
    {"object_type": "superevent", "query": {"field": "far", "op": "<", "value": 1e-10}}

Error responses always have the shape::

    {
        "error":   "invalid_query",
        "message": "<human-readable description>",
        "path":    "<dot-path to the offending node, or null>",
        "version": "2"
    }
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ...v1.superevents.views import *  # noqa: F401,F403

from ..filters import DjangoObjectAndGlobalPermissionsFilter
from .filters import V2SupereventSearchFilter, SupereventOrderingFilter, \
    _parse_body, _YAML_CONTENT_TYPES
from search.query.v2.translator import inject_default_filter, apply_query
from search.query.v2.validator import validate, QueryValidationError, format_path
from .filters import V2SearchError


def _v2_error(message, path=None):
    """Build a v2-format 400 error response payload."""
    return {
        'error': 'invalid_query',
        'message': message,
        'path': path,
        'version': '2',
    }


class SupereventViewSet(SupereventViewSet):  # noqa: F811
    """
    Superevent list/detail viewset with v2 structured query support.

    Identical to the v1 viewset except:
      - ``SupereventSearchFilter`` (text-based) is replaced by
        ``V2SupereventSearchFilter`` (JSON/YAML) for the GET list action.
      - A dedicated ``search`` POST action is added for body-based queries.
    """
    filter_backends = (
        DjangoObjectAndGlobalPermissionsFilter,
        V2SupereventSearchFilter,
        SupereventOrderingFilter,
    )

    def handle_exception(self, exc):
        """
        Intercept ``V2SearchError`` exceptions and return the structured
        payload directly, bypassing the GraceDB custom exception handler
        which would otherwise mangle dict details into character arrays.
        """
        if isinstance(exc, V2SearchError):
            return Response(
                exc.structured_payload,
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)

    def get_permissions(self):
        """
        The ``search`` action is a read-only operation.

        ``SupereventModelPermissions`` requires ``add_superevent`` for all
        POST requests except a small set of exempt URL names.  Since our
        ``search`` action is semantically a read operation, we use just
        ``IsAuthenticated`` (plus object-level guardian filtering enforced by
        the permission filter backend).
        """
        if self.action == 'search':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(methods=['post'], detail=False, url_path='search')
    def search(self, request, *args, **kwargs):
        """
        Search superevents with a structured JSON or YAML query body.

        The query parsing, validation, and execution are handled here directly
        (rather than via filter_backends) so that error responses can be
        returned as structured JSON dicts rather than propagating through the
        GraceDB custom exception handler which flattens dict details into
        character arrays.
        """
        import json
        import logging

        import yaml
        from superevents.models import Superevent

        logger = logging.getLogger(__name__)

        content_type = request.content_type or ''
        use_yaml = any(ct in content_type for ct in _YAML_CONTENT_TYPES)

        # Decode request body.
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

        # Fall back to URL parameter.
        if raw is None:
            raw = request.query_params.get('query')

        # No query supplied → return full accessible set.
        if not raw:
            qs = self._permission_filtered_queryset()
            return self._paginated_response(qs)

        # Parse JSON or YAML.
        try:
            if use_yaml:
                data = yaml.safe_load(raw)
            else:
                data = json.loads(raw)
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            return Response(
                _v2_error(f'Could not parse query body: {exc}'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(data, dict):
            return Response(
                _v2_error('Query body must be a JSON/YAML object.'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate object_type.
        declared_type = data.get('object_type')
        if declared_type is not None and declared_type != 'superevent':
            return Response(
                _v2_error(
                    f"object_type '{declared_type}' does not match this "
                    "endpoint (expected 'superevent').",
                    path='object_type',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        query_node = data.get('query', data)

        # Semantic validation.
        try:
            validate(query_node, 'superevent', strict=True)
        except QueryValidationError as exc:
            return Response(
                _v2_error(str(exc),
                          path=format_path(exc.path) if exc.path else None),
                status=status.HTTP_400_BAD_REQUEST,
            )

        query_node = inject_default_filter(query_node, 'superevent')

        try:
            filtered_qs = apply_query(Superevent, query_node, 'superevent')
        except Exception as exc:
            logger.exception('v2 superevent search execution failed')
            return Response(
                _v2_error(f'Query execution failed: {exc}'),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Intersect with permission-filtered queryset.
        perm_qs = self._permission_filtered_queryset()
        qs = perm_qs.filter(pk__in=filtered_qs.values('pk'))

        return self._paginated_response(qs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _permission_filtered_queryset(self):
        """
        Return the base queryset filtered through DjangoObjectAndGlobalPermissionsFilter
        and the ordering filter, but NOT the V2SupereventSearchFilter.
        """
        qs = self.get_queryset()
        for backend in (DjangoObjectAndGlobalPermissionsFilter,
                        SupereventOrderingFilter):
            qs = backend().filter_queryset(self.request, qs, self)
        return qs

    def _paginated_response(self, qs):
        """Paginate *qs* and return a Response."""
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
