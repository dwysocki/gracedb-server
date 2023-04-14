from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.urls import build_absolute_uri
from superevents.models import Log

register = template.Library()

template_link_format = "<a href='{notice_url}'>[Notice]</a> <a href='{circular_url}'>[Circular]</a>"


@register.filter(is_safe=True)
def latest_state_log(log_list):
    try:
        log = log_list.filter(
            tags__name="data_quality",
            comment__startswith="Detector state for active instruments is"
        ).latest("created")

        return mark_safe(log.comment)

    except Log.DoesNotExist:
        return "N/A"

@register.filter(is_safe=True)
def get_template_from_label(sevent):
    files_url = build_absolute_uri(reverse('superevents:file-list', args=[sevent.superevent_id]))
    if sevent.labels.filter(name='ADVOK'):
        notice_url = files_url + '{}-initial.json'.format(sevent.superevent_id)
        circular_url = files_url + 'initial-circular.txt'
    elif sevent.labels.filter(name='ADVNO'):
        notice_url = files_url + '{}-retraction.json'.format(sevent.superevent_id)
        circular_url = files_url + 'retraction-circular.txt'
    else:
        return "Advocate action (ADVOK/ADVNO) required"

    return mark_safe(template_link_format.format(notice_url=notice_url,
                                       circular_url=circular_url))

