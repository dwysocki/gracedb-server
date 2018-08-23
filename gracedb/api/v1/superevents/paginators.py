from collections import OrderedDict
import logging
import urllib

from rest_framework import pagination
from rest_framework.response import Response

# Set up logger
logger = logging.getLogger(__name__)


class CustomSupereventPagination(pagination.LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'count'
    offset_query_param = 'start'

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
        last_uri = base_uri + '?' + urllib.urlencode(param_dict)

        output = OrderedDict([
            ('numRows', numRows),
            ('superevents', data),
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
