from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as \
    RestFrameworkValidationError
from rest_framework import status, mixins
from rest_framework.response import Response

from ..models import Superevent
from .settings import SUPEREVENT_LOOKUP_FIELD, SUPEREVENT_LOOKUP_REGEX

import logging
logger = logging.getLogger(__name__)

class GetParentMixin(object):
    parent_lookup_field = None
    parent_queryset = None

    def get_parent(self):
        parent_value = self.kwargs.get(self.parent_lookup_field, None)
        if parent_value is None:
            raise KeyError('Lookup field not found')
        filter_kwargs = self.get_filter_kwargs(parent_value)
        parent = get_object_or_404(self.parent_queryset, **filter_kwargs)
        return parent

    def get_filter_kwargs(self, parent_value):
        return {'id': parent_value}


class GetParentSupereventMixin(GetParentMixin):
    parent_lookup_field = SUPEREVENT_LOOKUP_FIELD
    parent_queryset = Superevent.objects.all()

    def get_filter_kwargs(self, superevent_id):
        return Superevent.get_filter_kwargs_for_date_id_lookup(superevent_id)



class SafeDestroyMixin(mixins.DestroyModelMixin):
    """
    Copy of rest_framework's DestroyModelMixin which wraps
    the call to perform_destroy() in a try-except block for
    proper response handling.
    """
    destroy_error_classes = (Exception,)
    destroy_error_response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    destroy_error_message = None

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except self.destroy_error_classes as e:
            err_msg = self.destroy_error_message or e.__str__()
            return Response(err_msg, status=self.destroy_error_response_status)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SafeCreateMixin(mixins.CreateModelMixin):
    """
    Copy of rest_framework's CreateModelMixin which wraps
    the call to perform_destroy() in a try-except block for
    proper response handling.
    """
    create_error_classes = \
        (DjangoValidationError, RestFrameworkValidationError)
    create_error_response_status = status.HTTP_400_BAD_REQUEST
    create_error_message = None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except self.create_error_classes as e:
            err_msg = self.create_error_message or e.__str__()
            return Response(err_msg, status=self.create_error_response_status)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

