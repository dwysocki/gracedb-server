from collections import OrderedDict
from django.utils.functional import cached_property
from django.utils.http import urlencode
from rest_framework import pagination
from rest_framework.response import Response


class CustomEventPagination(pagination.LimitOffsetPagination):
    default_limit = 100
    limit_query_param = 'count'
    offset_query_param = 'start'
    

    # Override the built-in counting method from here:
    # https://github.com/encode/django-rest-framework/blob/3.4.7/rest_framework/pagination.py#L47
    # And see if it can be cached. Like suggested here:
    # https://stackoverflow.com/a/47357445
    # update: caching works but I noticed in the browser that sometimes the numRows
    # field retains its value from pervious queries. I don't know yet if it affects
    # data fetching in the API, but i'm going to leave it commented for now. 

    # Another update: it would seem that fetching just the integer row-id for query
    # results and then counting is faster than fetching the entire queryset. I didn't
    # observe any change when doing large-ish counts on dev1 (~33000 events), but 
    # maybe postgres gets clever enough when doing larger queries. I'll leave it in 
    # and see what happens: https://stackoverflow.com/a/47357445

#    @cached_property
    @property
    def _get_count(self):
        """
        Determine an object count, supporting either querysets or regular lists.
        """
        try:
            return self.queryset.values('id').count()
        except (AttributeError, TypeError):
            return len(self.queryset)


    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        self.queryset = queryset

        if self.limit is None:
            return None

        self.offset = self.get_offset(request)
        self.count = self._get_count
        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []
        return list(self.queryset[self.offset:self.offset + self.limit])

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
