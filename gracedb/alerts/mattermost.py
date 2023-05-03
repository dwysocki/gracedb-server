import logging

from django.conf import settings
from django.urls import reverse

from core.urls import build_absolute_uri
from events.shortcuts import is_event

from . import egad


# Set up logger
logger = logging.getLogger(__name__)


message_template = 'A superevent with GraceDB ID {sid} was created. [View]({url})'


def issue_mattermost_alerts_local(event_or_superevent, alert_type):
    # Not implemented
    pass


def issue_mattermost_alerts_egad(event_or_superevent, alert_type):
    # For now we're hard-coded to only issue new superevent alerts
    if is_event(event_or_superevent):
        return
    if alert_type != "new":
        return
    if (settings.TIER not in {"dev"}
        and not event_or_superevent.is_production):
        return

    superevent = event_or_superevent

    # For now we're hard-coded to the default channel
    channel_label = "default"

    # Construct the message, currently hard-coded to new superevents
    url = build_absolute_uri(reverse('superevents:view',
                                     args=[superevent.superevent_id]))
    message = message_template.format(sid=superevent.superevent_id, url=url)

    payload = {
        "channel_label": channel_label,
        "message": message,
    }

    egad.send_alert("mattermost", payload)


if settings.ENABLE_EGAD_MATTERMOST:
    issue_mattermost_alerts = issue_mattermost_alerts_egad
else:
    issue_mattermost_alerts = issue_mattermost_alerts_local
