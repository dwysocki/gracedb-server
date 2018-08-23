# Needed because our local events and superevents modules (for the API)
# shadow the names of the events and superevents apps.
from __future__ import absolute_import

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.http import HttpResponse, HttpResponseForbidden

from rest_framework import parsers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse as drf_reverse
from rest_framework.views import APIView

from api.backends import LigoAuthentication
from api.utils import api_reverse
from events.models import Group, Pipeline, Search, Tag, Label, EMGroup, \
    VOEvent, EMBBEventLog, EMSPECTRUM
from events.view_logic import get_performance_info
from superevents.models import Superevent
from ..superevents.url_templates import construct_url_templates


class TagList(APIView):
    """Tag List Resource
    """
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)

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
    authentication_classes = (LigoAuthentication,)
    permission_classes = (IsAuthenticated,)
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
            "voevent-types"  : dict(VOEvent.VOEVENT_TYPE_CHOICES),
        })


class PerformanceInfo(APIView):
    """
    Serialized performance information
    """
    authentication_classes = (LigoAuthentication,)
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
