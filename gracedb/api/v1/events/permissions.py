import logging

from rest_framework import permissions

# Set up logger
logger = logging.getLogger(__name__)


class CanUpdateGrbEvent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('events.t90_grbevent')
