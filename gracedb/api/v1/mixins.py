from __future__ import absolute_import
import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, mixins
from rest_framework.exceptions import ValidationError as \
    RestFrameworkValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

# Set up logger
logger = logging.getLogger(__name__)


class SafeDestroyMixin(mixins.DestroyModelMixin):
    """
    Copy of rest_framework's DestroyModelMixin which wraps
    the call to perform_destroy() in a try-except block for
    proper error handling.
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


class ValidateDestroyMixin(object):
    """
    Performs some validations on the instance or request data before
    the instance is destroyed.
    """
    def validate_destroy(self, request, instance):
        """
        Takes in request and instance for optional validation. This method
        should be overridden by subclasses.

        Output:
            Boolean indicating whether validation succeeded or not
            String indicating reason for failure (if success, return None)
        """
        return True, None

    def destroy(self, request, *args, **kwargs):
        # Get instance to be destroyed
        instance = self.get_object()

        # Perform validation
        request_ok, err_msg = self.validate_destroy(request, instance)
        if not request_ok:
            return Response(err_msg, status=status.HTTP_400_BAD_REQUEST)

        # If validated, destroy the instance and return 204
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SafeCreateMixin(mixins.CreateModelMixin):
    """
    Copy of rest_framework's CreateModelMixin which wraps
    the call to perform_create() in a try-except block for
    proper error handling.
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
            logger.error(e)
            err_msg = self.create_error_message or e.__str__()
            return Response(err_msg, status=self.create_error_response_status)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
            headers=headers)


class OrderedListModelMixin(object):
    """
    Identical to ListModelMixin from DRF, but implements ordering based on
    a user-provided tuple (list_view_order_by).
    """
    list_view_order_by = ()

    def __init__(self, **kwargs):
        super(OrderedListModelMixin, self).__init__(**kwargs)
        # Force list_view_order_by to be a tuple (easy for users
        # to mess this up with single-item tuples)
        assert isinstance(self.list_view_order_by, tuple), (
            'list_view_order_by must be a tuple'
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Custom ordering
        queryset = queryset.order_by(*self.list_view_order_by)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)


        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InheritDefaultPermissionsMixin(object):
    """
    Prepends default permissions from settings to list of class permissions.
    """
    permission_classes = ()

    def get_permissions(self):
        # Cast to lists to be safe, since these might be tuples
        permission_list = list(api_settings.DEFAULT_PERMISSION_CLASSES) + \
            list(self.permission_classes)
        return [permission() for permission in permission_list]
