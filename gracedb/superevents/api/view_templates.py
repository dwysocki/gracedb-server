from events.view_utils import reverse
from .views import SupereventViewSet, SupereventEventViewSet, \
    SupereventLabelViewSet, SupereventLogViewSet, SupereventLogTagViewSet, \
    SupereventFileViewSet, SupereventVOEventViewSet, \
    SupereventEMObservationViewSet


# Placeholder parameters for getting URLs with reverse
PH = {
    SupereventViewSet.lookup_field: 'S1234', # superevent_id
    SupereventEventViewSet.lookup_field: 'G1234', # graceid
    SupereventLabelViewSet.lookup_field: 'LABEL_NAME', # label name
    SupereventLogViewSet.lookup_field: '3333', # log number (N)
    SupereventLogTagViewSet.lookup_field: 'TAG_NAME', # tag name
    SupereventFileViewSet.lookup_field: 'FILE_NAME', # file name
    SupereventVOEventViewSet.lookup_field: '4444', # VOEvent number (N)
    SupereventEMObservationViewSet.lookup_field: '5555', # EMObservation number (N)
}


def construct_api_url_templates(request=None):
    # Bind our custom reverse for ease of use
    sr = lambda view_name, args=[]: reverse(view_name, args=[
        PH[SupereventViewSet.lookup_field]] + args, request=request)

    # Dict of views and temporary arguments which will be passed to reverse
    views = {
        'superevent-detail': [],
        'superevent-event-list': [],
        'superevent-event-detail': [PH[SupereventEventViewSet.lookup_field]],
        'superevent-label-list': [],
        'superevent-label-detail': [PH[SupereventLabelViewSet.lookup_field]],
        'superevent-log-list': [],
        'superevent-log-detail': [PH[SupereventLogViewSet.lookup_field]],
        'superevent-log-tag-list': [PH[SupereventLogViewSet.lookup_field]],
        'superevent-log-tag-detail': [PH[SupereventLogViewSet.lookup_field],
            PH[SupereventLogTagViewSet.lookup_field]],
        'superevent-file-list': [],
        'superevent-file-detail': [PH[SupereventFileViewSet.lookup_field]],
        'superevent-voevent-list': [],
        'superevent-voevent-detail': [
            PH[SupereventVOEventViewSet.lookup_field]],
        'superevent-emobservation-list': [],
        'superevent-emobservation-detail': [
            PH[SupereventEMObservationViewSet.lookup_field]],
        'superevent-confirm-as-gw': []
    }

    # Dict of URL templates:
    #  keys are view_name + '-template'
    #  values are URLs with placeholder parameters
    templates = {view + '-template': sr(view, args=args)
        for view, args in views.iteritems()}

    # Replace URL placeholder parameters with string formatting placeholders
    #   Ex: replace 'G1234' with '{graceid}'
    for k,v in templates.iteritems():
        for pattern,placeholder in PH.iteritems():
            if placeholder in v:
                v = v.replace(placeholder, "{{{0}}}".format(pattern))
        templates[k] = v

    return templates
