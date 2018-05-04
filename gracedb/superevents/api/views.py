from rest_framework import parsers
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
    remove_label_from_superevent

from core.vfile import VersionedFile
from events.models import Event, Label
from events.view_utils import reverse as gracedb_reverse
#from events.api.views import IsAuthorizedForPipeline, LigoLwRenderer
from events.api.backends import LigoAuthentication

from .mixins import GetParentSupereventMixin
from .paginators import BasePaginationFactory, CustomLabelPagination, \
    CustomLogTagPagination, CustomSupereventPagination
from .serializers import SupereventSerializer, SupereventUpdateSerializer, \
    SupereventEventSerializer, SupereventLabelSerializer, \
    SupereventLogSerializer, SupereventLogTagSerializer, \
    SupereventVOEventSerializer

from .settings import SUPEREVENT_LOOKUP_FIELD, SUPEREVENT_LOOKUP_REGEX

import os
import logging
logger = logging.getLogger(__name__)


class SupereventViewSet(viewsets.ModelViewSet):
    """
    View for listing all Superevents, retrieving individual superevents,
    creating new superevents, and updating existing superevents.
    """
    queryset = Superevent.objects.all()
    serializer_class = SupereventSerializer
    pagination_class = CustomSupereventPagination
    lookup_field = SUPEREVENT_LOOKUP_FIELD
    lookup_value_regex = SUPEREVENT_LOOKUP_REGEX

    def get_serializer_class(self):
        """Select a different serializer for updates"""
        serializer_class = self.serializer_class
        if self.request.method in ["PUT", "PATCH"]:
            serializer_class = SupereventUpdateSerializer
        return serializer_class

    def get_queryset(self):
        """Filter queryset for user"""
        # TODO: do we need to filter this any further?
        queryset = get_objects_for_user(self.request.user,
            'superevents.view_superevent')
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        superevent_id = self.kwargs.get(self.lookup_field)
        filter_kwargs = {'id': int(superevent_id[1:])}

        obj = get_object_or_404(queryset, **filter_kwargs)

        # TODO: figure this out
        self.check_object_permissions(self.request, obj)

        return obj


class SupereventEventViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.DestroyModelMixin,
                             GetParentSupereventMixin,
                             viewsets.GenericViewSet):
    """View for events attached to a superevent"""
    serializer_class = SupereventEventSerializer
    pagination_class = BasePaginationFactory(results_name='events')
    lookup_field = 'graceid'

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
                             viewsets.ModelViewSet):
    """Superevent labels"""
    serializer_class = SupereventLabelSerializer
    pagination_class = CustomLabelPagination
    lookup_field = 'label_name'

    def get_queryset(self):
        superevent = self.get_parent()
        # TODO: check whether user can view the superevent
        queryset = superevent.labelling_set.all()
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        label_name = self.kwargs.get(self.lookup_field, None)
        filter_kwargs = {'label__name': label_name}
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        remove_label_from_superevent(instance, request.user,
            add_log_message=True, issue_alert=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SupereventLogViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           GetParentSupereventMixin,
                           viewsets.GenericViewSet):
    """
    View for log messages attached to a superevent.
    """
    parser_class = parsers.FileUploadParser
    serializer_class = SupereventLogSerializer
    pagination_class = BasePaginationFactory(results_name='log')
    lookup_field = 'N'

    def get_queryset(self):
        superevent = self.get_parent()
        logger.warning('may need to filter logs for users')
        queryset = superevent.log_set.all().order_by('N')
        # filter for those tagged with external access tagname if is_external(request.user)
        return queryset

    # TODO: generalize this method, can be used for superevent, superevent-event, etc.
    def get_object(self):
        logger.warning('can probably do this generically on some mixin')
        queryset = self.filter_queryset(self.get_queryset())
        N = self.kwargs.get(self.lookup_field, None)
        filter_kwargs = {'N': N}
        obj = get_object_or_404(queryset, **filter_kwargs)
        logger.warning('check permissions here? or just in get_queryset?')
        return obj


class SupereventLogTagViewSet(GetParentSupereventMixin,
                              viewsets.ModelViewSet):
    """
    View for tags attached to a log message which is attached to a superevent.
    """
    serializer_class = SupereventLogTagSerializer
    pagination_class = CustomLogTagPagination
    lookup_field = 'tag_name'

    def get_parent_log(self):
        # TODO: check superevent permissions here
        parent_superevent = self.get_parent()
        return parent_superevent.log_set.get(N=self.kwargs.get('N'))

    def get_queryset(self):
        # TODO: for external users, check permissions on the log
        parent_log = self.get_parent_log()
        return parent_log.tags.all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        tag_name = self.kwargs.get(self.lookup_field, None)
        filter_kwargs = {'name': tag_name}
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj

    def perform_destroy(self, instance):
        parent_log = self.get_parent_log()
        remove_tag_from_log(parent_log, instance, self.request.user,
            add_log_message=True, issue_alert=True)

# TODO: add permissions to this viewset
class SupereventFileViewSet(GetParentSupereventMixin,
                            viewsets.ViewSet):
    """Superevent files"""
    lookup_field = 'file_name'

    def list(self, request, *args, **kwargs):
        parent_superevent = self.get_parent()
        files = parent_superevent.list_files(absolute_paths=False)
        file_list = {f: gracedb_reverse("superevent-file-detail",
            args=[parent_superevent.superevent_id, f], request=request)
            for f in files}
        return Response(file_list)

    def retrieve(self, request, *args, **kwargs):

        parent_superevent = self.get_parent()
        file_name = self.kwargs.get(self.lookup_field, None)
        file_path = os.path.join(parent_superevent.datadir, file_name)

        # Check if file exists:
        if not os.path.exists(file_path):
            err_msg = "File {0} not found for superevent {1}".format(file_name,
                parent_superevent.superevent_id)
            response = Response(err_msg, status=status.HTTP_404_NOT_FOUND)
        elif not os.access(file_path, os.R_OK):
            err_msg = "File {0} for superevent {1} is not readable".format(
                file_name, parent_superevent.superevent_id)
            response = Response(err_msg, status=
                status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif os.path.isfile(file_path):
            # Get an actual file.
            # If the user is external, check for authorization
            # TODO: update this
            #if is_external(request.user):
            #    if not check_external_file_access(superevent, file_name):
            #        msg = "You do not have permission to view this file."
            #        return HttpResponseForbidden(msg)
            # Try to figure out content type of file
            content_type, encoding = VersionedFile.guess_mimetype(file_path)
            content_type = content_type or "application/octet-stream"

            # Set up response object
            response = Response()

            # Use Apache XSendFile module to serve file
            response['X-Sendfile'] = file_path

            # For binary files, add as an attachment (will be downloaded from
            # browser instead of opened)
            if content_type == "application/octet-stream":
                response['Content-Disposition'] = \
                    'attachment; filename="{0}"'.format(os.path.basename(
                    file_name))

        return response


class SupereventVOEventViewSet(mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.CreateModelMixin,
                               GetParentSupereventMixin,
                               viewsets.GenericViewSet):
    """
    View for VOEvents attached to a superevent.
    """
    serializer_class = SupereventVOEventSerializer
    pagination_class = BasePaginationFactory(results_name='voevents')
    lookup_field = 'N'

    def get_queryset(self):
        superevent = self.get_parent()
        queryset = superevent.voevent_set.all()
        # filter for those tagged with external access tagname if is_external(request.user)
        return queryset

    # TODO: generalize this method, can be used for superevent, superevent-event, etc.
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        N = self.kwargs.get(self.lookup_field, None)
        filter_kwargs = {'N': N}
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj

