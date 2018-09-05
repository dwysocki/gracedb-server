from __future__ import absolute_import

from .views import SupereventViewSet, SupereventEventViewSet, \
    SupereventLabelViewSet, SupereventLogViewSet, SupereventLogTagViewSet, \
    SupereventFileViewSet, SupereventVOEventViewSet, \
    SupereventEMObservationViewSet, SupereventGroupObjectPermissionViewSet, \
    SupereventSignoffViewSet
from ...utils import api_reverse

# Placeholder parameters for getting URLs with reverse
PH = {
    SupereventViewSet.lookup_url_kwarg: 'S800106a', # superevent_id
    SupereventEventViewSet.lookup_url_kwarg: 'G1234', # graceid
    SupereventLabelViewSet.lookup_url_kwarg: 'LABEL_NAME', # label name
    SupereventLogViewSet.lookup_url_kwarg: '3333', # log number (N)
    SupereventLogTagViewSet.lookup_url_kwarg: 'TAG_NAME', # tag name
    SupereventFileViewSet.lookup_url_kwarg: 'FILE_NAME', # file name
    SupereventVOEventViewSet.lookup_url_kwarg: '4444', # VOEvent number (N)
    SupereventEMObservationViewSet.lookup_url_kwarg: '5555', # EMObservation
                                                             # number (N)
    SupereventSignoffViewSet.lookup_url_kwarg: 'TYPE_INST', # type + instrument
    SupereventGroupObjectPermissionViewSet.lookup_url_kwarg: 'GROUP_NAME',
}


def construct_url_templates(request=None):
    # Bind our custom reverse for ease of use
    sr = lambda view_name, args=[]: api_reverse('superevents:' + view_name,
        args=[PH[SupereventViewSet.lookup_url_kwarg]] + args, request=request)

    # Dict of views and temporary arguments which will be passed to reverse
    views = {
        'superevent-detail': [],
        'superevent-event-list': [],
        'superevent-event-detail': [PH[SupereventEventViewSet.lookup_url_kwarg]],
        'superevent-label-list': [],
        'superevent-label-detail': [PH[SupereventLabelViewSet.lookup_url_kwarg]],
        'superevent-log-list': [],
        'superevent-log-detail': [PH[SupereventLogViewSet.lookup_url_kwarg]],
        'superevent-log-tag-list': [PH[SupereventLogViewSet.lookup_url_kwarg]],
        'superevent-log-tag-detail': [PH[SupereventLogViewSet.lookup_url_kwarg],
            PH[SupereventLogTagViewSet.lookup_url_kwarg]],
        'superevent-file-list': [],
        'superevent-file-detail': [PH[SupereventFileViewSet.lookup_url_kwarg]],
        'superevent-voevent-list': [],
        'superevent-voevent-detail': [
            PH[SupereventVOEventViewSet.lookup_url_kwarg]],
        'superevent-emobservation-list': [],
        'superevent-emobservation-detail': [
            PH[SupereventEMObservationViewSet.lookup_url_kwarg]],
        'superevent-confirm-as-gw': [],
        'superevent-signoff-list': [],
        'superevent-signoff-detail': [
            PH[SupereventSignoffViewSet.lookup_url_kwarg]],
        'superevent-permission-list': [],
        'superevent-permission-modify': [],
    }

    # Dict of URL templates:
    #  keys are like '{view_name}-template'
    #  values are URLs with placeholder parameters
    templates = {view_name + '-template': sr(view_name, args=args)
        for view_name, args in views.iteritems()}

    # Replace URL placeholder parameters with string formatting placeholders
    #   Ex: replace 'G1234' with '{graceid}'
    for k,v in templates.iteritems():
        for pattern,placeholder in PH.iteritems():
            if placeholder in v:
                v = v.replace(placeholder, "{{{0}}}".format(pattern))
        templates[k] = v

    return templates
