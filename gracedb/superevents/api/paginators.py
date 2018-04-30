from rest_framework import pagination
from rest_framework.response import Response

from collections import OrderedDict

import logging
logger = logging.getLogger(__name__)


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
