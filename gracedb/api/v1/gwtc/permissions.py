import logging

from django.conf import settings
from django.urls import resolve

from rest_framework import permissions

from superevents.models import Superevent, Signoff
from ..permissions import FunctionalModelPermissions, \
    FunctionalObjectPermissions, FunctionalParentObjectPermissions

# Set up logger
logger = logging.getLogger(__name__)


class gwtc_model_permissions(FunctionalModelPermissions):
    authenticated_users_only = True
    allowed_methods = ['GET', 'POST']

    def get_post_permissions(self, request):
        # Just return the 'add_gwtc_catalog' perm for now until there
        # needs to be finer-grained control or new methods.
        return ['gwtc.add_gwtc_catalog']
