from django.shortcuts import get_object_or_404

from ..models import Superevent
from .settings import SUPEREVENT_LOOKUP_FIELD, SUPEREVENT_LOOKUP_REGEX


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
        # Currently, superevent_id ~ S0001, where 1 is the PK
        return {'id': int(superevent_id[1:])}

