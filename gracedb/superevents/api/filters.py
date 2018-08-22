from rest_framework import filters, exceptions

from django.http import HttpResponseBadRequest

from ..query import parseSupereventQuery

from pyparsing import ParseException
import logging
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
        except ParseException as e:
            raise exceptions.ParseError('Invalid query')

        return queryset.filter(filter_params)


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
            if f_s in self.field_map.keys():
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


class DjangoObjectAndGlobalPermissionsFilter(
    filters.DjangoObjectPermissionsFilter):
    """
    Same as DjangoObjectPermissionsFilter, except it allows global permissions.
    """
    accept_global_perms = True

    def filter_queryset(self, request, queryset, view):
        # Mostly from rest_framework.filters.DjangoObjectPermissionsFilter
        #
        # We want to defer this import until run-time, rather than import-time.
        # See https://github.com/encode/django-rest-framework/issues/4608
        # (Also see #1624 for why we need to make this import explicitly)
        from guardian.shortcuts import get_objects_for_user

        extra = {}
        user = request.user
        model_cls = queryset.model
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        permission = self.perm_format % kwargs
        extra['accept_global_perms'] = self.accept_global_perms

        return get_objects_for_user(user, permission, queryset, **extra)
