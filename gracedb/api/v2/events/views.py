"""
v2 event views.

Re-exports everything from v1, then:
  1. Overrides ``EventList.get`` to use the v2 structured query filter
     (``?query=<json>`` URL parameter) instead of the v1 text parser.
  2. Adds ``EventSearch`` — a POST endpoint at ``/api/v2/events/search/``
     that accepts a JSON or YAML query body without conflicting with the
     event-creation POST on the main list endpoint.

Usage::

    # GET with URL parameter:
    GET /api/v2/events/?query=<json>

    # POST body (JSON or YAML):
    POST /api/v2/events/search/
    Content-Type: application/json
    {"object_type": "event", "query": {"field": "group", "op": "=", "value": "CBC"}}
"""
from django.core.exceptions import FieldError

from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from ...v1.events.views import *  # noqa: F401,F403
from .filters import apply_v2_event_filter, V2EventSearchError

# Re-import module-level names used below so they don't depend on the wildcard
# import order.
from ...v1.events.views import (
    Event,
    EventSerializer,
    event_related_objects,
    event_prefetch_objects,
    PAGINATE_BY,
    xml_err_msg,
    is_external,
    FieldError,
    CustomEventPagination,
)


class EventList(EventList):  # noqa: F811
    """
    Event list with v2 structured query support (GET with ``?query=<json>``).

    POST (event creation) is inherited from v1 unchanged.
    """

    def get(self, request, *args, **kwargs):
        sort = request.query_params.get("sort", "-created")

        events = Event.objects.filter(graceid__isnull=False)

        if request.accepted_renderer.format == 'xml':
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest(xml_err_msg)

        request_is_external = is_external(request.user)

        # Apply v2 filter (raises V2EventSearchError → 400 on any query problem).
        try:
            events = apply_v2_event_filter(request, events)
        except V2EventSearchError as exc:
            return Response(exc.structured_payload, status=status.HTTP_400_BAD_REQUEST)

        try:
            events = events.order_by(sort).select_subclasses()
        except FieldError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        events = events.select_related(*event_related_objects) \
                       .prefetch_related(*event_prefetch_objects)

        serializer_context = {
            'request': request,
            'request_is_external': request_is_external,
        }
        paginated_results = self.paginator.paginate_queryset(events, request)
        serializer = EventSerializer(paginated_results, many=True,
                                     context=serializer_context)
        return self.paginator.get_paginated_response(serializer.data)


class EventSearch(InheritPermissionsAPIView):  # noqa: F821 — defined by wildcard import
    """
    POST endpoint for v2 structured event search.

    Accepts a JSON or YAML query body and returns the same paginated
    response format as ``GET /api/v2/events/``.
    """
    paginator = CustomEventPagination()

    def post(self, request, *args, **kwargs):
        sort = request.query_params.get("sort", "-created")

        events = Event.objects.filter(graceid__isnull=False)

        if request.accepted_renderer.format == 'xml':
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest(xml_err_msg)

        request_is_external = is_external(request.user)

        try:
            events = apply_v2_event_filter(request, events)
        except V2EventSearchError as exc:
            return Response(exc.structured_payload, status=status.HTTP_400_BAD_REQUEST)

        try:
            events = events.order_by(sort).select_subclasses()
        except FieldError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        events = events.select_related(*event_related_objects) \
                       .prefetch_related(*event_prefetch_objects)

        serializer_context = {
            'request': request,
            'request_is_external': request_is_external,
        }
        paginated_results = self.paginator.paginate_queryset(events, request)
        serializer = EventSerializer(paginated_results, many=True,
                                     context=serializer_context)
        return self.paginator.get_paginated_response(serializer.data)
