import logging

from superevents.models import Superevent
from superevents.utils import get_superevent_by_date_id_or_404
from .settings import SUPEREVENT_LOOKUP_URL_KWARG
from ..viewsets import NestedViewSet

# Set up logger
logger = logging.getLogger(__name__)


class SupereventNestedViewSet(NestedViewSet):
    """
    Gets a parent superevent object for a nested object by using the
    URL kwargs.  Also does a check on object permissions for the superevent,
    since some actions, like annotation, are controlled by a custom permission
    on the parent superevent itself.
    """
    parent_lookup_field = None # not needed due to custom lookup function
    parent_lookup_url_kwarg = SUPEREVENT_LOOKUP_URL_KWARG
    parent_queryset = Superevent.objects.all()
    parent_access_permission = 'superevents.view_superevent'
    check_permissions_on_parent_object = True

    def _set_parent(self):
        parent_lookup_value = self.get_parent_lookup_value()
        parent_queryset = self.get_parent_queryset()
        parent = get_superevent_by_date_id_or_404(parent_lookup_value,
            parent_queryset)
        self._parent = parent
