import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins, parsers, permissions, serializers, status, \
    viewsets, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..mixins import SafeCreateMixin, InheritDefaultPermissionsMixin
from gwtc.models import gwtc_catalog, gwtc_gevent, gwtc_superevent
from .serializers import gwtc_serializer
from .permissions import gwtc_model_permissions


class custom_gwtc_paginator(pagination.LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'count'
    offset_query_param = 'start'


class gwtc_viewset(SafeCreateMixin, InheritDefaultPermissionsMixin,
                   viewsets.ModelViewSet):
    queryset = gwtc_catalog.objects.all()
    serializer_class = gwtc_serializer 
    pagination_class = custom_gwtc_paginator
    permission_classes = (gwtc_model_permissions, )

    # This function gets called for 'list' methods, and returns a queryset. This
    # is called for `GET` requests to /api/gwtc/ and /api/gwtc/{number}
    def get_queryset(self):
        # filter the kwargs. 'number' might be none, depending on the request
        # address, in which case return the original queryset. 
        selected_number = self.kwargs.get('number')
        selected_version = self.kwargs.get('version')

        # if the catalog number is specified, then return the filtered queryset
        if selected_number:
            self.queryset = self.queryset.filter(number=selected_number)

        return self.queryset.prefetch_related('gwtc_superevent_set',
            'gwtc_superevent_set__superevent',
            'gwtc_superevent_set__gwtc_gevent_set',
            'gwtc_superevent_set__gwtc_gevent_set__gevent',
            'gwtc_superevent_set__gwtc_gevent_set__gevent__pipeline')

    # This function gets called for 'list' methods, and returns a queryset. This
    # is called for `GET` requests to /api/gwtc/{number}/{version}
    def get_object(self):
        # Get the kwargs from the request path. 
        selected_number = self.kwargs.get('number')
        selected_version = self.kwargs.get('version')

        # a request to 'latest' should return the latest value, so put in a special
        # case for that. 

        if selected_version.lower() == 'latest':
            selected_version = \
                 self.queryset.filter(number=selected_number).aggregate(Max('version'))['version__max']
        filter_kwargs = {'number': selected_number, 'version': selected_version}

        obj = get_object_or_404(self.queryset, **filter_kwargs)
            
        return obj
