from __future__ import absolute_import
from collections import OrderedDict
import logging
import os

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group as AuthGroup

from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins, parsers, permissions, serializers, status, \
    viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.file_utils import get_file_list
from core.http import check_and_serve_file
from core.vfile import VersionedFile
from events.models import Event, Label
from events.view_utils import reverse as gracedb_reverse
from superevents.buildVOEvent import VOEventBuilderException
from superevents.models import Superevent, Log, Signoff
from superevents.utils import remove_tag_from_log, \
    remove_event_from_superevent, remove_label_from_superevent, \
    confirm_superevent_as_gw, get_superevent_by_date_id_or_404, \
    expose_superevent, hide_superevent, delete_signoff
from .filters import SupereventSearchFilter, SupereventOrderingFilter
from .paginators import CustomSupereventPagination
from .permissions import SupereventModelPermissions, \
    SupereventObjectPermissions, SupereventLabellingModelPermissions, \
    EventParentSupereventPermissions, SupereventLogModelPermissions, \
    SupereventLogTagModelPermissions, SupereventLogTagObjectPermissions, \
    SupereventVOEventModelPermissions, ParentSupereventAnnotatePermissions, \
    SupereventSignoffModelPermissions, SupereventSignoffTypeModelPermissions, \
    SupereventSignoffTypeObjectPermissions, \
    SupereventGroupObjectPermissionPermissions
from .serializers import SupereventSerializer, SupereventUpdateSerializer, \
    SupereventEventSerializer, SupereventLabelSerializer, \
    SupereventLogSerializer, SupereventLogTagSerializer, \
    SupereventVOEventSerializer, SupereventEMObservationSerializer, \
    SupereventSignoffSerializer, SupereventGroupObjectPermissionSerializer
from .settings import SUPEREVENT_LOOKUP_URL_KWARG, SUPEREVENT_LOOKUP_REGEX
from .viewsets import SupereventNestedViewSet
from ..filters import DjangoObjectAndGlobalPermissionsFilter
from ..mixins import SafeCreateMixin, SafeDestroyMixin
from ..paginators import BasePaginationFactory, CustomLabelPagination, \
    CustomLogTagPagination
from ...utils import api_reverse

# Set up logger
logger = logging.getLogger(__name__)


class SupereventViewSet(SafeCreateMixin, viewsets.ModelViewSet):
    """
    View for listing all Superevents, retrieving individual superevents,
    creating new superevents, and updating existing superevents.
    """
    queryset = Superevent.objects.all()
    serializer_class = SupereventSerializer
    pagination_class = CustomSupereventPagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventModelPermissions, SupereventObjectPermissions,)
    lookup_url_kwarg = SUPEREVENT_LOOKUP_URL_KWARG
    lookup_value_regex = SUPEREVENT_LOOKUP_REGEX
    filter_backends = (DjangoObjectAndGlobalPermissionsFilter,
        SupereventSearchFilter, SupereventOrderingFilter,)
    ordering_fields = ('created', 't_0', 't_start', 't_end',
        'preferred_event__id', 't_0_date', 'is_gw', 'base_date_number',
        'gw_date_number', 'category')

    def get_serializer_class(self):
        """Select a different serializer for updates"""
        serializer_class = self.serializer_class
        if self.request.method in ["PUT", "PATCH"]:
            serializer_class = SupereventUpdateSerializer
        return serializer_class

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        superevent_id = self.kwargs.get(self.lookup_url_kwarg)

        # Get superevent by id
        obj = get_superevent_by_date_id_or_404(superevent_id, queryset)

        # Check permissions
        self.check_object_permissions(self.request, obj)

        return obj

    @action(methods=['post'], detail=True)
    def confirm_as_gw(self, request, *args, **kwargs):
        """Confirm a superevent as a GW"""
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
                             SupereventNestedViewSet):
    """View for events attached to a superevent"""
    serializer_class = SupereventEventSerializer
    pagination_class = BasePaginationFactory(results_name='events')
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        EventParentSupereventPermissions,)
    lookup_url_kwarg = 'graceid'
    destroy_error_classes = (Superevent.PreferredEventRemovalError,)
    destroy_error_response_status = status.HTTP_400_BAD_REQUEST

    def get_queryset(self):
        superevent = self.get_parent_object()
        queryset = superevent.events.all()
        # TODO: filter events for user (?)
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        graceid = self.kwargs.get(self.lookup_url_kwarg)
        filter_kwargs = {'id': int(graceid[1:])}
        event = get_object_or_404(queryset, **filter_kwargs)

        # Check event object permissions (?)
        self.check_object_permissions(self.request, event)

        return event

    def perform_destroy(self, instance):
        remove_event_from_superevent(instance.superevent, instance,
            self.request.user, add_superevent_log=True,
            add_event_log=True, issue_alert=True)


class SupereventLabelViewSet(viewsets.ModelViewSet,
                             SupereventNestedViewSet):
    """Superevent labels"""
    serializer_class = SupereventLabelSerializer
    pagination_class = CustomLabelPagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventLabellingModelPermissions,)
    lookup_url_kwarg = 'label_name'
    lookup_field = 'label__name'

    def get_queryset(self):
        superevent = self.get_parent_object()
        queryset = superevent.labelling_set.all().order_by('label__name')
        return queryset

    def perform_destroy(self, instance):
        remove_label_from_superevent(instance, self.request.user,
            add_log_message=True, issue_alert=True)


class SupereventLogViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           SafeCreateMixin,
                           SupereventNestedViewSet):
    """
    View for log messages attached to a superevent.
    """
    parser_class = parsers.FileUploadParser
    serializer_class = SupereventLogSerializer
    pagination_class = BasePaginationFactory(results_name='log')
    filter_backends = (DjangoObjectAndGlobalPermissionsFilter,)
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventLogModelPermissions, ParentSupereventAnnotatePermissions,)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'

    def get_queryset(self):
        # Get full set of logs for superevent
        superevent = self.get_parent_object()
        queryset = superevent.log_set.all().order_by('N')
        # NOTE: filtering of logs by view permissions is handled in
        # filter_queryset by the filter backends.

        return queryset


class SupereventLogTagViewSet(mixins.ListModelMixin,
                              mixins.RetrieveModelMixin,
                              SafeCreateMixin,
                              SafeDestroyMixin,
                              SupereventNestedViewSet):
    """
    View for tags attached to a log message which is attached to a superevent.
    """
    serializer_class = SupereventLogTagSerializer
    pagination_class = CustomLogTagPagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventLogTagModelPermissions, SupereventLogTagObjectPermissions,)
    lookup_url_kwarg = 'tag_name'
    lookup_field = 'name'

    def _set_parent_log(self):
        """Gets and caches parent log object"""
        # Get parent log object, which is nested below parent superevent
        parent_superevent = self.get_parent_object()

        # Pass full set of logs for parent superevent to get_objects_for_user,
        # which will filter based on view permissions
        parent_log_queryset = get_objects_for_user(self.request.user,
            'superevents.view_log', parent_superevent.log_set.all())

        # Get parent_log and cache it; return 404 if not found
        self._parent_log = get_object_or_404(parent_log_queryset,
            **{'N': self.kwargs.get('N')})

    def get_parent_log(self):
        # If parent log is not cached, try to get it and cache it.
        if not hasattr(self, '_parent_log'):
            self._set_parent_log()
        return self._parent_log

    def get_queryset(self):
        parent_log = self.get_parent_log()
        return parent_log.tags.all().order_by('name')

    def perform_destroy(self, instance):
        parent_log = self.get_parent_log()
        remove_tag_from_log(parent_log, instance, self.request.user,
            add_log_message=True, issue_alert=False)


class SupereventFileViewSet(SupereventNestedViewSet):
    """Superevent files"""
    lookup_url_kwarg = 'file_name'

    def get_log_queryset(self):
        # Get full list of logs for parent superevent
        parent_superevent = self.get_parent_object()
        return parent_superevent.log_set.all()

    def filter_log_queryset(self, log_queryset):
        # Filter queryset based on the user's view permissions
        return get_objects_for_user(self.request.user,
            'superevents.view_log', log_queryset)

    def list(self, request, *args, **kwargs):
        # Get logs which are viewable by the current user and
        # have files attached
        parent_superevent = self.get_parent_object()
        viewable_logs = self.filter_log_queryset(self.get_log_queryset())

        # Get list of filenames
        file_list = get_file_list(viewable_logs, parent_superevent.datadir)

        # Compile sorted dict of filenames and links
        file_dict = OrderedDict((f,
            api_reverse('superevents:superevent-file-detail',
            args=[parent_superevent.superevent_id, f], request=request))
            for f in sorted(file_list))

        return Response(file_dict)

    def retrieve(self, request, *args, **kwargs):
        # Get parent superevent
        parent_superevent = self.get_parent_object()

        # Get file name from URL kwargs
        full_filename = self.kwargs.get(self.lookup_url_kwarg)

        # Try to split into name,version (for log lookup)
        filename, version = Log.split_versioned_filename(full_filename)

        # Get logs which are viewable by the current user and
        # have files attached
        filtered_logs = self.filter_log_queryset(self.get_log_queryset())

        # If no version provided, it's a symlink to the most recent version.
        # So we follow the symlink and get the version that way.
        if version is None:
            full_file_path = os.path.join(parent_superevent.datadir, filename)
            target_file = os.path.realpath(full_file_path)
            target_basename = os.path.basename(target_file)
            _, version = Log.split_versioned_filename(target_basename)

        # Get specific log based on filename and version to check if user has
        # access.
        log = get_object_or_404(filtered_logs, **{'filename': filename,
            'file_version': version})

        # Get full file path for serving
        parent_superevent = self.get_parent_object()
        file_path = os.path.join(parent_superevent.datadir, full_filename)
        return check_and_serve_file(request, file_path, ResponseClass=Response)


class SupereventVOEventViewSet(mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               SafeCreateMixin,
                               SupereventNestedViewSet):
    """
    View for VOEvents attached to a superevent.
    """
    serializer_class = SupereventVOEventSerializer
    pagination_class = BasePaginationFactory(results_name='voevents')
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventVOEventModelPermissions,)
    create_error_classes = (VOEventBuilderException)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'

    def get_queryset(self):
        superevent = self.get_parent_object()
        queryset = superevent.voevent_set.all()
        return queryset


class SupereventEMObservationViewSet(mixins.ListModelMixin,
                                     mixins.RetrieveModelMixin,
                                     SafeCreateMixin,
                                     SupereventNestedViewSet):
    """
    View for EMObservations attached to a superevent.
    """
    serializer_class = SupereventEMObservationSerializer
    pagination_class = BasePaginationFactory(results_name='observations')
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        ParentSupereventAnnotatePermissions,)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'

    def get_queryset(self):
        superevent = self.get_parent_object()
        queryset = superevent.emobservation_set.all()
        return queryset


class SupereventSignoffViewSet(viewsets.ModelViewSet,
                               SafeCreateMixin,
                               SupereventNestedViewSet):
    """
    View for signoffs associated with a superevent.
    """
    serializer_class = SupereventSignoffSerializer
    pagination_class = BasePaginationFactory(results_name='signoffs')
    # Order of the 'model' and 'type' permissions matters for the
    # error messages to make sense.
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventSignoffModelPermissions,
        SupereventSignoffTypeModelPermissions,
        SupereventSignoffTypeObjectPermissions,)
    lookup_url_kwarg = 'typeinst' # signoff_type + instrument

    def get_queryset(self):
        superevent = self.get_parent_object()
        queryset = superevent.signoff_set.all()
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # lookup_url_kwarg is like 'TYPEINSTRUMENT'
        type_instrument = self.kwargs.get(self.lookup_url_kwarg)

        # Try to split on signoff type. If a split happens, then
        # set the instrument and break out. Otherwise, we take
        # instrument='' and take the full lookup_url_kwarg as the
        # signoff_type
        filter_kwargs = {'instrument': ''}
        for _type, _ in Signoff.SIGNOFF_TYPE_CHOICES:
            type_inst_tuple = type_instrument.split(_type)

            if (len(type_inst_tuple) == 2):
                filter_kwargs['instrument'] = type_inst_tuple[1]
                break
        filter_kwargs['signoff_type'] = _type

        # Get signoff or 404 
        signoff = get_object_or_404(queryset, **filter_kwargs)

        # Check object permissions
        self.check_object_permissions(self.request, signoff)

        return signoff

    def perform_destroy(self, instance):
        delete_signoff(instance, self.request.user, add_log_message=True,
            issue_alert=True)


class SupereventGroupObjectPermissionViewSet(viewsets.ModelViewSet,
                                             SafeCreateMixin,
                                             SafeDestroyMixin,
                                             SupereventNestedViewSet):
    """
    View for object permissions associated with exposing/hiding
    a superevent to/from LV-EM users or the public.
    """
    serializer_class = SupereventGroupObjectPermissionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
        SupereventGroupObjectPermissionPermissions,)
    pagination_class = BasePaginationFactory(results_name='permissions')

    def get_queryset(self):
        superevent = self.get_parent_object()
        return superevent.supereventgroupobjectpermission_set.all()

    @action(methods=['post'], detail=False)
    def modify(self, request, superevent_id):
        """
        Expose or hide a superevent by creating or deleting
        GroupObjectPermissions
        """

        # Get superevent
        superevent = self.get_parent_object()

        # Get action from data
        action = request.data.get('action', None)

        # Validation
        if action not in ['expose', 'hide']:
            return Response('action must be \'expose\' or \'hide\'',
                status=status.HTTP_400_BAD_REQUEST)

        # We make exposing and hiding a superevent idempotent
        # so as to prevent possible errors due to multi-user
        # race conditions
        if action == 'expose' and not superevent.is_exposed:
            expose_superevent(superevent, request.user, add_log_message=True,
                issue_alert=True)
        elif action == 'hide' and superevent.is_exposed:
            hide_superevent(superevent, request.user, add_log_message=True,
                issue_alert=True)

        # Return list of permissions
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
