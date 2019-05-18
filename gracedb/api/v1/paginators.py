from collections import OrderedDict
import logging

from django.utils.http import urlencode

from rest_framework import pagination
from rest_framework.response import Response

# Set up logger
logger = logging.getLogger(__name__)

# TP (30 Apr 2018):
# This module has a bunch of hacked together pagination which is intended
# to match the existing "pagination" of the events API.  We should definitely
# redo both APIs to do something reasonable and consistent when we have a
# chance.


def BasePaginationFactory(links_dict=True, results_name='results'):
    class CustomBasePagination(pagination.PageNumberPagination):
        generate_links = links_dict
        results_key = results_name
    
        def get_paginated_response(self, data):
            output = OrderedDict([
                ('start', 0),
                ('numRows', len(data)),
                (self.results_key, data),
            ])
    
            if self.generate_links:
                link_dict = OrderedDict([
                    ('self', self.request.build_absolute_uri()),
                    ('first', self.request.build_absolute_uri()),
                    ('last', self.request.build_absolute_uri()),
                ])
                output['links'] = link_dict
    
            return Response(output)

    return CustomBasePagination


class CustomLabelPagination(pagination.PageNumberPagination):
    def get_paginated_response(self, data):
        output = OrderedDict([
            ('labels', data),
            ('links',
                OrderedDict([
                    ('self', self.request.build_absolute_uri()),
                    ('superevent', self.request.build_absolute_uri()),
                ])),
        ])

        return Response(output)


class CustomLogTagPagination(pagination.PageNumberPagination):
    def get_paginated_response(self, data):
        output = OrderedDict([
            ('tags', data),
        ])

        return Response(output)


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
        last_uri = base_uri + '?' + urlencode(param_dict)

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
