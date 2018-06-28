from rest_framework import parsers
from rest_framework.decorators import action
from rest_framework.renderers import BaseRenderer, JSONRenderer, \
    BrowsableAPIRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import mixins, parsers, serializers, status
from guardian.shortcuts import get_objects_for_user

from django.http import HttpResponse
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from ..models import Superevent
from ..utils import remove_tag_from_log, remove_event_from_superevent, \
    remove_label_from_superevent, confirm_superevent_as_gw, \
    get_superevent_by_date_id_or_404

from core.vfile import VersionedFile
from core.http import check_and_serve_file
from events.models import Event, Label
from events.view_utils import reverse as gracedb_reverse
#from events.api.views import IsAuthorizedForPipeline, LigoLwRenderer
from events.api.backends import LigoAuthentication

from ..buildVOEvent import VOEventBuilderException
from .filters import SupereventSearchFilter, SupereventOrderingFilter
from .mixins import GetParentSupereventMixin, BaseGetObjectMixin, \
    SafeDestroyMixin, SafeCreateMixin
from .paginators import BasePaginationFactory, CustomLabelPagination, \
    CustomLogTagPagination, CustomSupereventPagination
from .serializers import SupereventSerializer, SupereventUpdateSerializer, \
    SupereventEventSerializer, SupereventLabelSerializer, \
    SupereventLogSerializer, SupereventLogTagSerializer, \
    SupereventVOEventSerializer, SupereventEMObservationSerializer
from .settings import SUPEREVENT_LOOKUP_FIELD, SUPEREVENT_LOOKUP_REGEX

import os
import logging
logger = logging.getLogger(__name__)


class SupereventViewSet(SafeCreateMixin, viewsets.ModelViewSet):
    """
    View for listing all Superevents, retrieving individual superevents,
    creating new superevents, and updating existing superevents.
    """
    queryset = Superevent.objects.all()
    serializer_class = SupereventSerializer
    pagination_class = CustomSupereventPagination
    lookup_field = SUPEREVENT_LOOKUP_FIELD
    lookup_value_regex = SUPEREVENT_LOOKUP_REGEX
    filter_backends = (SupereventSearchFilter, SupereventOrderingFilter,)
    ordering_fields = ('created', 't_0', 't_start', 't_end',
        'preferred_event__id', 't_0_date', 'is_gw', 'base_date_number',
        'gw_date_number')

    def get_serializer_class(self):
        """Select a different serializer for updates"""
        serializer_class = self.serializer_class
        if self.request.method in ["PUT", "PATCH"]:
            serializer_class = SupereventUpdateSerializer
        return serializer_class

    def get_queryset(self):
        """Filter queryset for user"""
        # TODO: do we need to filter this any further?
        # TODO: Check that this might be causing slowness
        #queryset = get_objects_for_user(self.request.user,
        #    'superevents.view_superevent')
        queryset = self.queryset
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        superevent_id = self.kwargs.get(self.lookup_field)

        obj = get_superevent_by_date_id_or_404(self.request, superevent_id)

        # TODO: figure this out
        self.check_object_permissions(self.request, obj)

        return obj

    @action(methods=['post'], detail=True)
    def confirm_as_gw(self, request, superevent_id):
        # TODO: permissions checking!!

        # Get superevent
        superevent = self.get_object()

        # If already a GW, return an error
        if not superevent.is_gw:
            confirm_superevent_as_gw(superevent, self.request.user)
        else:
            return Response('Superevent is already confirmed as a GW',
                status=status.HTTP_400_BAD_REQUEST)

        # Return data
        serializer = self.get_serializer(superevent)
        return Response(serializer.data)


class SupereventEventViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             SafeDestroyMixin,
                             GetParentSupereventMixin,
                             viewsets.GenericViewSet):
    """View for events attached to a superevent"""
    serializer_class = SupereventEventSerializer
    pagination_class = BasePaginationFactory(results_name='events')
    lookup_field = 'graceid'
    destroy_error_classes = (Superevent.PreferredEventRemovalError,)
    destroy_error_response_status = status.HTTP_400_BAD_REQUEST

    def get_queryset(self):
        superevent = self.get_parent()
        queryset = superevent.events.all()
        # TODO: filter events for user
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        graceid = self.kwargs.get(self.lookup_field)
        filter_kwargs = {'id': int(graceid[1:])}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # TODO: figure this out
        self.check_object_permissions(self.request, obj)

        return obj

    def perform_destroy(self, instance):
        remove_event_from_superevent(instance.superevent, instance,
            self.request.user, add_superevent_log=True,
            add_event_log=True, issue_superevent_alert=True,
            issue_event_alert=True)


class SupereventLabelViewSet(GetParentSupereventMixin,
                             BaseGetObjectMixin,
                             viewsets.ModelViewSet):
    """Superevent labels"""
    serializer_class = SupereventLabelSerializer
    pagination_class = CustomLabelPagination
    lookup_field = 'label_name'
    query_field = 'label__name'

    def get_queryset(self):
        superevent = self.get_parent()
        # TODO: check whether user can view the superevent
        queryset = superevent.labelling_set.all()
        return queryset

    def perform_destroy(self, instance):
        remove_label_from_superevent(instance, self.request.user,
            add_log_message=True, issue_alert=True)


class SupereventLogViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           SafeCreateMixin,
                           GetParentSupereventMixin,
                           BaseGetObjectMixin,
                           viewsets.GenericViewSet):
    """
    View for log messages attached to a superevent.
    """
    parser_class = parsers.FileUploadParser
    serializer_class = SupereventLogSerializer
    pagination_class = BasePaginationFactory(results_name='log')
    lookup_field = 'N'

    # TODO: filter logs for viewers
    def get_queryset(self):
        superevent = self.get_parent()
        queryset = superevent.log_set.all().order_by('N')
        # filter for those tagged with external access tagname if is_external(request.user)
        return queryset


class SupereventLogTagViewSet(GetParentSupereventMixin,
                              BaseGetObjectMixin,
                              viewsets.ModelViewSet,
                              SafeCreateMixin):
    """
    View for tags attached to a log message which is attached to a superevent.
    """
    serializer_class = SupereventLogTagSerializer
    pagination_class = CustomLogTagPagination
    lookup_field = 'tag_name'
    query_field = 'name'

    def get_parent_log(self):
        # TODO: check superevent permissions here
        parent_superevent = self.get_parent()
        return parent_superevent.log_set.get(N=self.kwargs.get('N'))

    def get_queryset(self):
        # TODO: for external users, check permissions on the log
        parent_log = self.get_parent_log()
        return parent_log.tags.all()

    def perform_destroy(self, instance):
        parent_log = self.get_parent_log()
        remove_tag_from_log(parent_log, instance, self.request.user,
            add_log_message=True, issue_alert=False)


# TODO: add permissions to this viewset
class SupereventFileViewSet(GetParentSupereventMixin,
                            viewsets.ViewSet):
    """Superevent files"""
    lookup_field = 'file_name'

    def list(self, request, *args, **kwargs):
        parent_superevent = self.get_parent()
        files = parent_superevent.list_files(absolute_paths=False)
        file_list = {f: gracedb_reverse("superevents:superevent-file-detail",
            args=[parent_superevent.superevent_id, f], request=request)
            for f in files}
        return Response(file_list)

    def retrieve(self, request, *args, **kwargs):

        parent_superevent = self.get_parent()
        file_name = self.kwargs.get(self.lookup_field, None)
        file_path = os.path.join(parent_superevent.datadir, file_name)

        return check_and_serve_file(request, file_path, ResponseClass=Response)


class SupereventVOEventViewSet(mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               SafeCreateMixin,
                               GetParentSupereventMixin,
                               BaseGetObjectMixin,
                               viewsets.GenericViewSet):
    """
    View for VOEvents attached to a superevent.
    """
    serializer_class = SupereventVOEventSerializer
    pagination_class = BasePaginationFactory(results_name='voevents')
    lookup_field = 'N'
    create_error_classes = (VOEventBuilderException)

    def get_queryset(self):
        superevent = self.get_parent()
        queryset = superevent.voevent_set.all()
        # filter for those tagged with external access tagname if is_external(request.user)
        return queryset


class SupereventEMObservationViewSet(mixins.ListModelMixin,
                                     mixins.RetrieveModelMixin,
                                     SafeCreateMixin,
                                     GetParentSupereventMixin,
                                     viewsets.GenericViewSet):
    """
    View for EMObservations attached to a superevent.
    """
    serializer_class = SupereventEMObservationSerializer
    pagination_class = BasePaginationFactory(results_name='observations')
    lookup_field = 'N'

    def get_queryset(self):
        superevent = self.get_parent()
        queryset = superevent.emobservation_set.all()
        # filter for those tagged with external access tagname if is_external(request.user)
        return queryset

