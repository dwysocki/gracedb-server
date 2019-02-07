import logging

from django.conf import settings

from rest_framework import permissions

# Set up logger
logger = logging.getLogger(__name__)


class IsPriorityUser(permissions.BasePermission):
    """Only allow users in the priority users group"""
    message = 'You are not authorized to use this API.'

    def has_permission(self, request, view):
        return request.user.groups.filter(
            name=settings.PRIORITY_USERS_GROUP).exists()
