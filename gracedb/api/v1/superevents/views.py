from __future__ import absolute_import
from collections import OrderedDict, defaultdict
import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins, parsers, permissions, serializers, status, \
    viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.file_utils import get_file_list
from core.http import check_and_serve_file
from core.vfile import FileVersionError, FileVersionNameError
from events.models import Event, Label
from events.view_utils import reverse as gracedb_reverse
from ligoauth.utils import is_internal
from superevents.models import Superevent, Log, Signoff, VOEvent
from superevents.utils import remove_tag_from_log, \
    remove_event_from_superevent, remove_label_from_superevent, \
    confirm_superevent_as_gw, get_superevent_by_date_id_or_404, \
    get_superevent_by_sid_or_gwid_or_404, \
    expose_superevent, hide_superevent, delete_signoff, \
    remove_pipeline_preferred_event_from_superevent
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
from .serializers import (
    SupereventSerializer, SupereventUpdateSerializer,
    SupereventEventSerializer, SupereventLabelSerializer,
    SupereventLogSerializer, SupereventLogTagSerializer,
    SupereventVOEventSerializer, SupereventVOEventSerializerExternal,
    SupereventEMObservationSerializer, SupereventSignoffSerializer,
    SupereventGroupObjectPermissionSerializer,
    SupereventPipelinePreferredEventSerializer
)
from .settings import SUPEREVENT_LOOKUP_URL_KWARG, SUPEREVENT_LOOKUP_REGEX
from .viewsets import SupereventNestedViewSet
from ..filters import DjangoObjectAndGlobalPermissionsFilter
from ..mixins import SafeCreateMixin, SafeDestroyMixin, ValidateDestroyMixin, \
    InheritDefaultPermissionsMixin, LogPrefetchModelMixin, \
    LabellingPrefetchModelMixin
from ..paginators import BasePaginationFactory, CustomLabelPagination, \
    CustomLogTagPagination
from ...utils import api_reverse

# Retry imports:
from time import sleep

# Set up logger
logger = logging.getLogger(__name__)

# Retrying parameters: 
EFS_RETRY_MAX = 5
EFS_RETRY_WAIT = 0.01

APIWEB_ROOT = 'apiweb'

# Add select_related and prefetch_related parameters:
EVENT_SELECT_RELATED = ('pipeline', 'group', 'search', 'submitter',
    'superevent', 'grbevent', 'neutrinoevent', 'coincinspiralevent',
    'mlyburstevent', 'multiburstevent', 'lalinferenceburstevent',
    'siminspiralevent'
)
SEVENT_SELECT_RELATED = ('preferred_event',
    'preferred_event__pipeline',
    'preferred_event__group',
    'preferred_event__search',
    'preferred_event__submitter',
    'preferred_event__superevent',
    'preferred_event__grbevent',
    'preferred_event__neutrinoevent',
    'preferred_event__coincinspiralevent',
    'preferred_event__mlyburstevent',
    'preferred_event__multiburstevent',
    'preferred_event__lalinferenceburstevent',
    'preferred_event__siminspiralevent',
)


class SupereventViewSet(SafeCreateMixin, InheritDefaultPermissionsMixin,
    viewsets.ModelViewSet):
    """
    View for listing all Superevents, retrieving individual superevents,
    creating new superevents, and updating existing superevents.
    """
    queryset = Superevent.objects.all()
    serializer_class = SupereventSerializer
    pagination_class = CustomSupereventPagination
    permission_classes = (SupereventModelPermissions,
        SupereventObjectPermissions,)
    lookup_url_kwarg = SUPEREVENT_LOOKUP_URL_KWARG
    lookup_value_regex = SUPEREVENT_LOOKUP_REGEX
    filter_backends = (DjangoObjectAndGlobalPermissionsFilter,
        SupereventSearchFilter, SupereventOrderingFilter,)
    ordering_fields = ('created', 't_0', 't_start', 't_end',
        'preferred_event__id', 't_0_date', 'is_gw', 'base_date_number',
        'gw_date_number', 'category',
        'default_superevent_id',
        'time_coinc_far','space_coinc_far','em_type')

    def get_queryset(self):

        SEVENT_EVENT_PREFETCH = Prefetch('events', 
            queryset=Event.objects.select_related(*EVENT_SELECT_RELATED))
        SEVENT_EXTEVENT_PREFETCH = Prefetch('events', 
            queryset=Event.objects.filter(group__name=settings.EXTERNAL_ANALYSIS_GROUP)\
            .select_related(*EVENT_SELECT_RELATED),
            to_attr='external_events')
        SEVENT_INTEVENT_PREFETCH = Prefetch('events', 
            queryset=Event.objects.exclude(group__name=settings.EXTERNAL_ANALYSIS_GROUP)\
            .select_related(*EVENT_SELECT_RELATED),
            to_attr='internal_events')
        SEVENT_PPEVENT_PREFETCH = Prefetch('pipeline_preferred_events',
            queryset=Event.objects.select_subclasses()\
                .select_related(*EVENT_SELECT_RELATED))
        SEVENT_PREFETCH_SET = (SEVENT_EVENT_PREFETCH,
            SEVENT_EXTEVENT_PREFETCH,
            SEVENT_INTEVENT_PREFETCH,
            SEVENT_PPEVENT_PREFETCH,
            'labels'
        )

        return self.queryset\
            .select_related(*SEVENT_SELECT_RELATED)\
            .prefetch_related(*SEVENT_PREFETCH_SET)

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
        obj = get_superevent_by_sid_or_gwid_or_404(superevent_id, queryset)

        # Check permissions
        self.check_object_permissions(self.request, obj)

        return obj

    @action(methods=['post'], detail=True)
    def confirm_as_gw(self, request, *args, **kwargs):
        """Confirm a superevent as a GW"""
        # Get superevent
        superevent = self.get_object()

        # Get gw_id from request, if it exists:
        gw_id = request.data.get('gw_id')

        # If already a GW, return an error
        if not superevent.is_gw:
            try:
                confirm_superevent_as_gw(superevent, self.request.user, gw_id)
            except ValidationError as e:
                return Response(e.__str__(),
                        status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response('Superevent is already confirmed as a GW',
                status=status.HTTP_400_BAD_REQUEST)

        # Return data
        serializer = self.get_serializer(superevent)
        return Response(serializer.data)

class SupereventEventViewSet(ValidateDestroyMixin,
    InheritDefaultPermissionsMixin, SupereventNestedViewSet):
    """View for events attached to a superevent"""
    serializer_class = SupereventEventSerializer
    pagination_class = BasePaginationFactory(results_name='events')
    permission_classes = (EventParentSupereventPermissions,
        permissions.IsAuthenticated,)
    lookup_url_kwarg = 'graceid'
    list_view_order_by = ('pk',)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        graceid = self.kwargs.get(self.lookup_url_kwarg)
        filter_kwargs = {'id': int(graceid[1:])}
        event = get_object_or_404(queryset, **filter_kwargs)

        # Check event object permissions (?)
        self.check_object_permissions(self.request, event)

        return event

    def validate_destroy(self, request, instance):
        # Don't allow removal of preferred events

        # NOTE: instance should be an event attached to the superevent
        # in question.  All other events are filtered out when we get
        # and filter the queryset.  So if instance has the
        # superevent_preferred_for attribute, it must be the preferred event.
        if hasattr(instance, 'superevent_preferred_for'):
            err_msg = ("Event {gid} can't be removed from superevent {sid} "
                "because it is the preferred event").format(
                gid=instance.graceid, sid=instance.superevent.graceid)
            return False, err_msg
        else:
            return True, None

    def perform_destroy(self, instance):
        remove_event_from_superevent(instance.superevent, instance,
            self.request.user, add_superevent_log=True,
            add_event_log=True, issue_alert=True)


class SupereventPipelinePreferredEventViewSet(ValidateDestroyMixin,
    InheritDefaultPermissionsMixin, SupereventNestedViewSet):
    """View for pipeline preferred events attributed to a superevent"""
    serializer_class = SupereventPipelinePreferredEventSerializer
    pagination_class = BasePaginationFactory(results_name='pipeline_preferred_events')
    permission_classes = (EventParentSupereventPermissions,
        permissions.IsAuthenticated,)
    lookup_url_kwarg = 'graceid'
    list_view_order_by = ('pk',)

    def get_queryset(self):
        superevent_id = self.kwargs['superevent_id']
        superevent_obj = get_superevent_by_sid_or_gwid_or_404(superevent_id)
        return superevent_obj.pipeline_preferred_events.all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        graceid = self.kwargs.get(self.lookup_url_kwarg)
        filter_kwargs = {'id': int(graceid[1:])}
        event = get_object_or_404(queryset, **filter_kwargs)

        # Check event object permissions (?)
        self.check_object_permissions(self.request, event)

        return event

    def validate_destroy(self, request, instance):
        # Don't allow removal of preferred events, same as in the events
        # list.

        if hasattr(instance, 'superevent_preferred_for'):
            err_msg = ("Event {gid} can't be removed from superevent {sid}'s "
                "pipeline preferred list because it is the preferred event").format(
                gid=instance.graceid, sid=instance.superevent.graceid)
            return False, err_msg
        else:
            return True, None

    # FIXME: turn on igwn-alerts once we settle on alert contents
    def perform_destroy(self, instance):
        remove_pipeline_preferred_event_from_superevent(instance.superevent,
            instance, self.request.user, add_superevent_log=True,
            add_event_log=True, issue_alert=False)

class SupereventLabelViewSet(ValidateDestroyMixin,
    InheritDefaultPermissionsMixin,  LabellingPrefetchModelMixin,
    SupereventNestedViewSet):
    """Superevent labels"""
    serializer_class = SupereventLabelSerializer
    pagination_class = CustomLabelPagination
    permission_classes = (SupereventLabellingModelPermissions,)
    lookup_url_kwarg = 'label_name'
    lookup_field = 'label__name'
    list_view_order_by = ('label__name',)

    def validate_destroy(self, request, instance):
        # Don't allow removal of protected labels
        if instance.label.protected:
            err_msg = ('The label \'{label}\' is managed by an automated '
                'process and cannot be removed manually').format(
                label=instance.label.name)
            return False, err_msg
        else:
            return True, None

    def perform_destroy(self, instance):
        remove_label_from_superevent(instance, self.request.user,
            add_log_message=True, issue_alert=True)


class SupereventLogViewSet(SafeCreateMixin, InheritDefaultPermissionsMixin,
    LogPrefetchModelMixin, SupereventNestedViewSet):
    """
    View for log messages attached to a superevent.
    """
    parser_class = parsers.FileUploadParser
    serializer_class = SupereventLogSerializer
    pagination_class = BasePaginationFactory(results_name='log')
    filter_backends = (DjangoObjectAndGlobalPermissionsFilter,)
    permission_classes = (SupereventLogModelPermissions,
        ParentSupereventAnnotatePermissions,)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'
    list_view_order_by = ('N',)


class SupereventLogTagViewSet(SafeCreateMixin, SafeDestroyMixin,
    InheritDefaultPermissionsMixin, SupereventNestedViewSet):
    """
    View for tags attached to a log message which is attached to a superevent.
    """
    serializer_class = SupereventLogTagSerializer
    pagination_class = CustomLogTagPagination
    permission_classes = (SupereventLogTagModelPermissions,
        SupereventLogTagObjectPermissions,)
    lookup_url_kwarg = 'tag_name'
    lookup_field = 'name'
    list_view_order_by = ('name',)

    def _set_parent_log(self):
        """Gets and caches parent log object"""
        # Get parent log object, which is nested below parent superevent
        parent_superevent = self.get_parent_object()

        # Pass full set of logs for parent superevent to get_objects_for_user,
        # which will filter based on view permissions
        parent_log_queryset = get_objects_for_user(self.request.user,
            'superevents.view_log', klass=parent_superevent.log_set.all())

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
        return parent_log.tags.all()

    def perform_destroy(self, instance):
        parent_log = self.get_parent_log()
        remove_tag_from_log(parent_log, instance, self.request.user,
            add_log_message=True, issue_alert=False)


class SupereventFileViewSet(InheritDefaultPermissionsMixin,
    SupereventNestedViewSet):
    """Superevent files"""
    lookup_url_kwarg = 'file_name'

    def get_log_queryset(self):
        # Filter logs with non-empty filenames and order them efficiently
        parent_superevent = self.get_parent_object()
        return parent_superevent.log_set.filter(filename__gt='').order_by('-created', '-N')

    def filter_log_queryset(self, log_queryset):
        # Use guardian to filter logs based on user permissions
        return get_objects_for_user(
            self.request.user,
            'superevents.view_log',
            klass=log_queryset
        )

    # This is a bandaid to overcome some very very
    # intermittent errors we've been seeing on AWS.
    # I'm going to let this play on playground and test
    # and if it doesn't fail castastropically, I'll
    # move it into production before the root cause
    # can be determined.
    
    def list(self, request, *args, **kwargs):
        efs_access_attempt = 1
        efs_access_success = False

        # Get logs which are viewable by the current user and
        # have files attached
        parent_superevent = self.get_parent_object()
        logs = self.filter_log_queryset(self.get_log_queryset())

        while not efs_access_success:
            try: 
                versioned_files = set()
                symlinks = set()
                latest_versions = defaultdict(lambda: 0)

                # Track latest version per filename
                for log in parent_superevent.log_set.filter(filename__gt=''):
                    latest_versions[log.filename] = max(latest_versions[log.filename], log.file_version)

                # Add versioned filenames and symlinks if latest version is exposed
                for log in logs:
                    if log.filename:
                        versioned_name = f"{log.filename},{log.file_version}"
                        versioned_files.add(versioned_name)

                        if log.file_version == latest_versions.get(log.filename):
                            symlinks.add(log.filename)

                all_files = versioned_files.union(symlinks)

                file_dict = OrderedDict(
                    (f, api_reverse('superevents:superevent-file-detail',
                                    args=[parent_superevent.superevent_id, f],
                                    request=request))
                    for f in sorted(all_files)
                )

            except OSError:
                logger.warning("Retrying EFS access. Attempt number "
                        "{}".format(efs_access_attempt))
                sleep(EFS_RETRY_WAIT)
                efs_access_attempt += 1
                if efs_access_attempt > EFS_RETRY_MAX:
                    return Response("File system hiccup, please retry",
                            status=status.HTTP_409_CONFLICT)
            else:
                efs_access_success = True

        return Response(file_dict)

    # This is a bandaid to overcome some very very
    # intermittent errors we've been seeing on AWS.
    # I'm going to let this play on playground and test
    # and if it doesn't fail castastropically, I'll
    # move it into production before the root cause
    # can be determined.

    def retrieve(self, request, *args, **kwargs):
        efs_access_attempt = 1
        efs_access_success = False

        # Get parent superevent
        parent_superevent = self.get_parent_object()

        # Get file name from URL kwargs
        full_filename = self.kwargs.get(self.lookup_url_kwarg)

        while not efs_access_success:
            try:

                # Try to split into name,version (for log lookup)
                try:
                    filename, version = Log.split_versioned_filename(full_filename)
                except FileVersionError as e:
                    # Bad version specifier
                    return Response('File not found, version string should be an int',
                        status=status.HTTP_404_NOT_FOUND)
                except FileVersionNameError as e:
                    # File name doesn't match versioning scheme (likely has a comma
                    # in it that isn't part of the versioning scheme)
                    return Response(('Invalid filename: filename should not contain '
                        'commas'), status=status.HTTP_400_BAD_REQUEST)
        
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
        
                response = check_and_serve_file(request, file_path, ResponseClass=Response)
        
                # if the request is for apiweb, set the cache max-age equal to the cache 
                # on the public page. the primary use case for this is showing images 
                # on the public and on superevent pages. 
                if request.path.split('/')[1] == APIWEB_ROOT:
                    response.headers['Cache-control'] = f'max-age={settings.PUBLIC_PAGE_CACHING}'

                return response

            except OSError:
                logger.warning("Retrying EFS access. Attempt number "
                        "{}".format(efs_access_attempt))
                sleep(EFS_RETRY_WAIT)
                efs_access_attempt += 1
                if efs_access_attempt > EFS_RETRY_MAX:
                    return Response("File system hiccup, please retry",
                            status=status.HTTP_409_CONFLICT)
            else:
                efs_access_success = True


class SupereventVOEventViewSet(SafeCreateMixin, InheritDefaultPermissionsMixin,
    SupereventNestedViewSet):
    """
    View for VOEvents attached to a superevent.
    """
    serializer_class = SupereventVOEventSerializer
    pagination_class = BasePaginationFactory(results_name='voevents')
    permission_classes = (SupereventVOEventModelPermissions,)
    create_error_classes = (VOEvent.VOEventBuilderException)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'
    list_view_order_by = ('N',)

    def get_serializer_class(self):
        if is_internal(self.request.user):
            return self.serializer_class
        else:
            return SupereventVOEventSerializerExternal


class SupereventEMObservationViewSet(SafeCreateMixin,
    InheritDefaultPermissionsMixin, SupereventNestedViewSet):
    """
    View for EMObservations attached to a superevent.
    """
    serializer_class = SupereventEMObservationSerializer
    pagination_class = BasePaginationFactory(results_name='observations')
    permission_classes = (ParentSupereventAnnotatePermissions,)
    lookup_url_kwarg = 'N'
    lookup_field = 'N'
    list_view_order_by = ('N',)


class SupereventSignoffViewSet(SafeCreateMixin, InheritDefaultPermissionsMixin,
    SupereventNestedViewSet):
    """
    View for signoffs associated with a superevent.
    """
    serializer_class = SupereventSignoffSerializer
    pagination_class = BasePaginationFactory(results_name='signoffs')
    # Order of the 'model' and 'type' permissions matters for the
    # error messages to make sense.
    permission_classes = (SupereventSignoffModelPermissions,
        SupereventSignoffTypeModelPermissions,
        SupereventSignoffTypeObjectPermissions,)
    lookup_url_kwarg = 'typeinst' # signoff_type + instrument
    list_view_order_by = ('signoff_type', 'instrument',)

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


class SupereventGroupObjectPermissionViewSet(SafeCreateMixin,
    SafeDestroyMixin, InheritDefaultPermissionsMixin, SupereventNestedViewSet):
    """
    View for object permissions associated with exposing/hiding
    a superevent to/from LV-EM users or the public.
    """
    serializer_class = SupereventGroupObjectPermissionSerializer
    permission_classes = (SupereventGroupObjectPermissionPermissions,)
    pagination_class = BasePaginationFactory(results_name='permissions')
    list_view_order_by = ('group',)

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
