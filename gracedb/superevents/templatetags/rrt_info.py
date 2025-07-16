from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.urls import build_absolute_uri
from superevents.models import Log

register = template.Library()

template_link_format = "<a href='{notice_url}'>[Notice]</a> <a href='{circular_url}'>[Circular]</a>"
dqr_link_format = "<a href='https://ldas-jobs.ligo.caltech.edu/~dqr/o4dqr/online/events/{yearmonth}/{sid}/5_min_tier_index.html' target='_blank'>[Data Quality Report]</a>"


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

    # Get filename based on label, or return the advreq message:
    if sevent.labels.filter(name='ADVOK'):
        notice_filename = '{}-initial.json'.format(sevent.superevent_id)
        if sevent.labels.filter(name='RAVEN_ALERT'):
            circular_filename = 'initial-emcoinc-circular.txt'
        else:
            circular_filename = 'initial-circular.txt'

    elif sevent.labels.filter(name='ADVNO'):
        notice_filename = '{}-retraction.json'.format(sevent.superevent_id)
        circular_filename = 'retraction-circular.txt'

    else:
        return mark_safe("Advocate action (<span style='font-family: monospace;'>ADVOK/ADVNO</span>) required")

    # Build the files URL:
    notice_url = build_absolute_uri(reverse('api:default:superevents:superevent-file-detail',
        args=[sevent.superevent_id, notice_filename]))
    circular_url = build_absolute_uri(reverse('api:default:superevents:superevent-file-detail',
        args=[sevent.superevent_id, circular_filename]))

    return mark_safe(template_link_format.format(notice_url=notice_url,
                                       circular_url=circular_url))

@register.filter(is_safe=True)
def get_dqr_status(sevent):

    # Is the DQR reqest label present?
    if sevent.labels.filter(name='DQR_REQUEST'):
       return mark_safe(dqr_link_format.format(yearmonth=sevent.created.strftime("%Y%m"),
           sid=sevent.superevent_id))
    else:
        return mark_safe("<span style='font-family: monospace;'>DQR_REQUEST</span> label not applied")

@register.filter(is_safe=True)
def get_rrt_skymap_url(sevent):

    # Pipelines have various conventions for skymap names:
    if sevent.preferred_event.pipeline.name == 'aframe':
        skymap_filename = 'amplfi'
    elif sevent.preferred_event.group.name == 'Burst':
        skymap_filename = sevent.preferred_event.pipeline.name.lower()
    else:
        skymap_filename = 'bayestar'

    return build_absolute_uri(reverse('api:default:superevents:superevent-file-detail',
        args=[sevent.superevent_id, f'{skymap_filename}.png']))
