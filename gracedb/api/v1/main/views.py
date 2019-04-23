# Needed because our local events and superevents modules (for the API)
# shadow the names of the events and superevents apps.
from __future__ import absolute_import
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.http import unquote_plus

from rest_framework import parsers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse as drf_reverse
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView

from api.backends import GraceDbX509FullCertAuthentication, \
    GraceDbX509CertInfosAuthentication
from api.utils import api_reverse
from events.models import Group, Pipeline, Search, Tag, Label, EMGroup, \
    VOEvent, EMBBEventLog, EMSPECTRUM, SignoffBase
from events.view_logic import get_performance_info
from superevents.models import Superevent
from .serializers import UserSerializer
from ..mixins import InheritDefaultPermissionsMixin
from ..superevents.url_templates import construct_url_templates

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


class TagList(APIView):
    """Tag List Resource
    """

    def get(self, request):
        # Return a list of links to all tag objects.
        tag_dict = {}
        for tag in Tag.objects.all():
            tag_dict[tag.name] = { 
                'displayName': tag.displayName,
                'blessed': tag.name in settings.BLESSED_TAGS
            }
        rv = {'tags' : tag_dict}
        return Response(rv)


class GracedbRoot(APIView):
    """
    Root of the Gracedb REST API
    """
    parser_classes = ()

    def get(self, request):
        # XXX This seems like a scummy way to get a URI template.
        # Is there better?
        detail = api_reverse("events:event-detail", args=["G1200"], request=request)
        detail = detail.replace("G1200", "{graceid}")
        log = api_reverse("events:eventlog-list", args=["G1200"], request=request)
        log = log.replace("G1200", "{graceid}")
        log_detail = api_reverse("events:eventlog-detail", args=["G1200", "3333"],
            request=request)
        log_detail = log_detail.replace("G1200", "{graceid}")
        log_detail = log_detail.replace("3333", "{N}")
        voevent = api_reverse("events:voevent-list", args=["G1200"], request=request)
        voevent = voevent.replace("G1200", "{graceid}")
        voevent_detail = api_reverse("events:voevent-detail", args=["G1200", "3333"],
            request=request)
        voevent_detail = voevent_detail.replace("G1200", "{graceid}")
        voevent_detail = voevent_detail.replace("3333", "{N}")
        embb = api_reverse("events:embbeventlog-list", args=["G1200"], request=request)
        embb = embb.replace("G1200", "{graceid}")
        emo = api_reverse("events:emobservation-list", args=["G1200"], request=request)
        emo = emo.replace("G1200", "{graceid}")
        emo_detail = api_reverse("events:emobservation-detail", args=["G1200", "3333"],
            request=request)
        emo_detail= emo_detail.replace("G1200", "{graceid}")
        emo_detail= emo_detail.replace("3333", "{N}")

        files = api_reverse("events:files", args=["G1200", "filename"], request=request)
        files = files.replace("G1200", "{graceid}")
        files = files.replace("filename", "{filename}")

        labels = api_reverse("events:labels", args=["G1200", "thelabel"], request=request)
        labels = labels.replace("G1200", "{graceid}")
        labels = labels.replace("thelabel", "{label}")

        taglist = api_reverse("events:eventlogtag-list", args=["G1200", "0"], request=request)
        taglist = taglist.replace("G1200", "{graceid}")
        taglist = taglist.replace("0", "{N}")

        tag = api_reverse("events:eventlogtag-detail", args=["G1200", "0", "tagname"], request=request)
        tag = tag.replace("G1200", "{graceid}")
        tag = tag.replace("0", "{N}")
        tag = tag.replace("tagname", "{tag_name}")

        signofflist = api_reverse("events:signoff-list", args=["G1200"], request=request)
        signofflist = signofflist.replace("G1200", "{graceid}")

        # XXX Need a template for the tag list?

        templates = {
                "event-detail-template" : detail,
                "voevent-list-template" : voevent,
                "voevent-detail-template" : voevent_detail,
                "event-log-template" : log,
                "event-log-detail-template" : log_detail,
                "emobservation-list-template": emo,
                "emobservation-detail-template": emo_detail,
                "embb-event-log-template" : embb,
                "event-label-template" : labels,
                "files-template" : files,
                "tag-template" : tag,
                "taglist-template" : taglist,
                "signoff-list-template": signofflist,
                }

        # Get superevent templates
        superevent_templates = construct_url_templates(request)
        templates.update(superevent_templates)

        return Response({
            "links" : {
                "superevents" : api_reverse("superevents:superevent-list",
                    request=request),
                "events"      : api_reverse("events:event-list", request=request),
                "self"        : api_reverse("root", request=request),
                "performance" : api_reverse("performance-info", request=request),
                "user-info": api_reverse("user-info", request=request),
                },
            "templates" : templates,
            "groups"    : [group.name for group in Group.objects.all()],
            "pipelines" : [pipeline.name for pipeline in
                Pipeline.objects.all()],
            "searches"  : [search.name for search in Search.objects.all()],
            "labels"    : [label.name for label in Label.objects.all()],
            "em-groups"  : [g.name for g in EMGroup.objects.all()],
            "wavebands"      : dict(EMSPECTRUM),
            "eel-statuses"   : dict(EMBBEventLog.EEL_STATUS_CHOICES),
            "obs-statuses"   : dict(EMBBEventLog.OBS_STATUS_CHOICES),
            "superevent-categories": 
                dict(Superevent.SUPEREVENT_CATEGORY_CHOICES),
            "signoff-types": dict(SignoffBase.SIGNOFF_TYPE_CHOICES),
            "signoff-statuses": dict(SignoffBase.OPERATOR_STATUS_CHOICES),
            "instruments": dict(SignoffBase.INSTRUMENT_CHOICES),
            "voevent-types"  : dict(VOEvent.VOEVENT_TYPE_CHOICES),
            "api-versions": api_settings.ALLOWED_VERSIONS,
            "server-version": settings.PROJECT_VERSION,
            # Maintained for backwards compatibility with client
            "API_VERSIONS": api_settings.ALLOWED_VERSIONS,
        })


class PerformanceInfo(InheritDefaultPermissionsMixin, APIView):
    """
    Serialized performance information
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (parsers.MultiPartParser,)

    def get(self, request, *args, **kwargs):
        user_groups = set(request.user.groups.all())
        allowed_groups = set([])
        try:
            allowed_groups = set([
                AuthGroup.objects.get(name=settings.LVC_GROUP),
                AuthGroup.objects.get(name=settings.EXEC_GROUP),
            ])
        except:
            pass

        if not user_groups & allowed_groups:
            return HttpResponseForbidden("Forbidden")

        try:
            performance_info = get_performance_info()
        except Exception, e:
            return Response(str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(performance_info, status=status.HTTP_200_OK)


class UserInfoView(RetrieveAPIView):
    serializer_class = UserSerializer

    #def get_serializer_class(self):
    #    # Override so we can use custom behavior for unauthenticated users
    #    if self.request.user.is_anonymous():
    #        return AnonymousUserSerializer
    #    else:
    #        return self.serializer_class

    def retrieve(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            output = {'username': 'AnonymousUser'}
        else:
            instance = request.user
            serializer = self.get_serializer(instance)
            output = serializer.data
        return Response(output)


class CertDebug(APIView):
    """
    Certificate debugging
    """

    def get(self, request):
        d = {}

        # Set up backend
        backend = GraceDbX509FullCertAuthentication()

        # Raw cert data
        d['raw_cert'] = str(request.META.get(backend.cert_header,
            'Header not found'))

        # Get certificate data
        try:
            cert_data = backend.get_certificate_data_from_request(request)
        except Exception as e:
            d['result'] = 'Error getting cert data from request: {0}'.format(e)
            return Response(d)

        if cert_data is None:
            d['result'] = 'No cert data found'
            return Response(d)

        # Try to verify cert
        try:
            certificate = backend.verify_certificate_chain(cert_data)
        except Exception as e:
            d['result'] = "Error verifying certificate: {0}".format(e)
            return Response(d)

        # Add data to response
        d['hash'] = certificate.get_subject().hash()
        d['subject_components'] = certificate.get_subject().get_components()
        d['subject'] = backend.get_certificate_subject_string(certificate)
        d['issuer_components'] = certificate.get_issuer().get_components()
        d['issuer'] = backend.get_certificate_issuer_string(certificate)

        return Response(d)


class CertInfosDebug(APIView):
    """
    Certificate infos debugging
    """

    def get(self, request):
        d = {}

        # Set up backend
        backend = GraceDbX509CertInfosAuthentication()

        # Raw cert data
        raw_infos = request.META.get(backend.infos_header, None)
        if raw_infos is None:
            d['raw_infos'] = 'Header not found'
            d['result'] = 'No cert infos found'
            return Response(d)
        d['raw_infos'] = str(raw_infos)

        # Get certificate info
        infos = request.META.get(backend.infos_header, None)

        # Unquote (handle pluses -> spaces)
        infos_unquoted = unquote_plus(infos)

        # Extract subject and issuer
        try:
            subject, issuer = backend.infos_pattern.search(infos_unquoted).groups()
        except Exception as e:
            d['result'] = ("Couldn't match infos pattern to extract subject "
                "and issuer: {0}").format(e)
            return Response(d)

        # Get "official" subject
        subject = backend.get_cert_dn_from_request(request)

        d['subject'] = subject
        d['issuer'] = backend.convert_format(issuer)

        return Response(d)
