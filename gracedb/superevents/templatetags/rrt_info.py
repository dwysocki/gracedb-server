from django import template
from django.utils.safestring import mark_safe

from superevents.models import Log

register = template.Library()


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
