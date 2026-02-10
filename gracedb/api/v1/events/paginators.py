from collections import OrderedDict

from django.conf import settings
from django.core.cache import cache
from django.utils.http import urlencode
from rest_framework import pagination
from rest_framework.response import Response

from api.utils import get_count_cache_key


class CustomEventPagination(pagination.LimitOffsetPagination):
    default_limit = settings.EVENT_PAGINATION_DEFAULT_LIMIT
    max_limit = settings.EVENT_PAGINATION_MAX_LIMIT
    limit_query_param = 'count'
    offset_query_param = 'start'

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.offset = self.get_offset(request)

        # Try to get count from cache
        cache_key = get_count_cache_key(
            request, 'event', self.limit_query_param, self.offset_query_param)
        count = cache.get(cache_key)
        if count is None:
            # Use values('id').count() as it can be faster for large querysets
            try:
                count = queryset.values('id').count()
            except (AttributeError, TypeError):
                count = len(queryset)
            cache.set(cache_key, count, settings.QUERY_COUNT_CACHE_TIMEOUT)

        self.count = count

        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []

        return list(queryset[self.offset:self.offset + self.limit])

    def get_paginated_response(self, data):
        numRows = self.count

        # Get base URI
        base_uri = self.request.build_absolute_uri(self.request.path)

        # Construct custom link for "last" page
        last = max(0, (numRows / self.limit)) * self.limit
        param_dict = {
            'start': last,
            self.limit_query_param: self.limit,
        }
        last_uri = base_uri + '?' + urlencode(param_dict)

        output = OrderedDict([
            ('numRows', numRows),
            ('events', data),
            ('links',
                OrderedDict([
                    ('self', self.request.build_absolute_uri()),
                    ('next', self.get_next_link()),
                    ('previous', self.get_previous_link()),
                    ('first', base_uri),
                    ('last', last_uri),
                ])),
        ])
        return Response(output)
