from __future__ import absolute_import
import logging

from django.conf import settings

from events.shortcuts import is_event
from .email import issue_email_alerts
from .phone import issue_phone_alerts
from .recipients import ALERT_TYPE_RECIPIENT_GETTERS
from .xmpp import issue_xmpp_alerts


# Set up logger
logger = logging.getLogger(__name__)


def issue_alerts(event_or_superevent, alert_type, serialized_object,
    serialized_parent=None, **kwargs):

    # Send XMPP alert
    if settings.SEND_XMPP_ALERTS:
        issue_xmpp_alerts(event_or_superevent, alert_type, serialized_object,
            serialized_parent=serialized_parent)

    # Below here, we only do processing for email and phone alerts ------------

    # A few checks on whether we should issue a phone and/or email alert ------
    if not (settings.SEND_EMAIL_ALERTS or settings.SEND_PHONE_ALERTS):
        return

    # Phone and email alerts are only issued for certain alert types
    # We check this by looking at the keys of ALERT_TYPE_RECIPIENT_GETTERS
    if (alert_type not in ALERT_TYPE_RECIPIENT_GETTERS):
        return

    # Don't send phone or email alerts for MDC or Test cases, or offline
    if is_event(event_or_superevent):
        # Test/MDC events
        event = event_or_superevent
        if event.is_mdc() or event.is_test():
            return

        # Offline events
        if event.offline:
            return
    else:
        # Test/MDC superevents
        s = event_or_superevent
        if s.is_mdc() or s.is_test():
            return

        # Superevents with offline preferred events
        if s.preferred_event.offline:
            return

    # Looks like we're going to issue phone and/or email alerts ---------------

    # Get recipient getter class
    rg_class = ALERT_TYPE_RECIPIENT_GETTERS[alert_type]

    # Instantiate recipient getter
    rg = rg_class(event_or_superevent, **kwargs)

    # Get recipients
    email_recipients, phone_recipients = rg.get_recipients()

    # Try to get label explicitly from kwargs
    label = kwargs.get('label', None)

    # Issue phone alerts
    if settings.SEND_PHONE_ALERTS and phone_recipients.exists():
        issue_phone_alerts(event_or_superevent, alert_type, phone_recipients,
            label=label)

    # Issue email alerts
    if settings.SEND_EMAIL_ALERTS and email_recipients.exists():
        issue_email_alerts(event_or_superevent, alert_type, email_recipients,
            label=label)
