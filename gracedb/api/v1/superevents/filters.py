from __future__ import absolute_import
import logging
from pyparsing import ParseException

from django.http import HttpResponseBadRequest

from rest_framework import filters, exceptions

from search.forms import se_gpstime_parseerror
from search.query.labels import filter_for_labels
from search.query.superevents import parseSupereventQuery

# Set up logger
logger = logging.getLogger(__name__)


class SupereventSearchFilter(filters.SearchFilter):
    search_param = 'query'

    def get_search_terms(self, request):
        # Custom because we don't want default behavior of splitting on spaces
        return request.query_params.get(self.search_param, '')

    def filter_queryset(self, request, queryset, view):
        query = self.get_search_terms(request)

        # TODO: do we want to do this?
        # If no query, we still set a blank query and pass things through to
        # query parser so as to perform the default filtering out of Test and
        # MDC superevents
        #if not query:
        #    query = ''
        # Currently, we just return the full queryset
        if not query:
            return queryset

        # Do filtering
        try:
            filter_params = parseSupereventQuery(query)
            qs = queryset.filter(filter_params)
            qs = filter_for_labels(qs, query)
        except ParseException as e:
            raise exceptions.ParseError('Invalid query')
        except KeyError as e:
            raise exceptions.ParseError(se_gpstime_parseerror(e))
        return qs


class SupereventOrderingFilter(filters.OrderingFilter):
    ordering_param = 'sort'
    field_map = {
        'preferred_event': u'preferred_event__id',
        'id': [u't_0_date', u'is_gw', u'gw_date_number', 'base_date_number'],
        'superevent_id': [u't_0_date', u'is_gw', u'gw_date_number',
            'base_date_number'],
    }

    def custom_field_mapping(self, fields):
        out_fields = []
        for f in fields:
            prefix = '-' if f.startswith('-') else ''
            f_s = f.lstrip('-')
            if f_s in self.field_map:
                mapped_fields = self.field_map[f_s]
                if not isinstance(mapped_fields, list):
                    mapped_fields = [mapped_fields]
                if prefix:
                    mapped_fields = [prefix + f for f in mapped_fields]
                out_fields.extend(mapped_fields)
            else:
                out_fields.append(f)
        return out_fields

    def get_ordering(self, request, queryset, view):
        """
        Same as base class get_ordering method except we add in custom
        mappings between ordering keywords and fields.
        """
        # Get ordering fields from request query params
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]

            # Get custom field mappings
            fields = self.custom_field_mapping(fields)

            # Remove invalid fields
            ordering = self.remove_invalid_fields(queryset, fields, view,
                request)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)
