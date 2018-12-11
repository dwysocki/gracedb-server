from __future__ import absolute_import
import json
import logging
import os
import socket
from subprocess import Popen, PIPE, STDOUT
import sys

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import EmailMessage
from django.db.models import QuerySet, Q
from django.urls import reverse

from core.time_utils import gpsToUtc
from events.models import Event
from events.permission_utils import is_external
from events.shortcuts import is_event
from search.query.labels import filter_for_labels
from superevents.shortcuts import is_superevent
from userprofile.models import Contact
from .email import issue_email_alerts
from .phone import issue_phone_alerts
from .xmpp import issue_xmpp_alerts

# Set up logger
logger = logging.getLogger(__name__)


def get_alert_recips(event_or_superevent):

    if is_superevent(event_or_superevent):
        # TODO: update for superevents
        pass
    elif is_event(event_or_superevent):
        event = event_or_superevent
        # Queryset of all triggers for this pipeline
        triggers = event.pipeline.trigger_set.filter(labels=None)
        # Filter on FAR threshold requirements
        query = Q(farThresh__isnull=True)
        if event.far:
            query |= Q(farThresh__lt=event.far)
        triggers = triggers.filter(query)
        # Contacts for all triggers, make sure user is in LVC group (safeguard)
        contacts = Contact.objects.filter(trigger__in=triggers,
            user__groups__name=settings.LVC_GROUP).select_related('user')
        email_recips = contacts.exclude(email="")
        phone_recips = contacts.exclude(phone="")

    return email_recips, phone_recips


def get_alert_recips_for_label(event_or_superevent, label):
    # Blank QuerySets for recipients
    email_recips = QuerySet()
    phone_recips = QuerySet()

    # Construct a queryset containing only this object; needed for
    # call to filter_for_labels
    qs = event_or_superevent._meta.model.objects.filter(
        pk=event_or_superevent.pk)

    # Triggers on given label matching pipeline OR with no pipeline;
    # no pipeline indicates that pipeline is irrelevant
    if is_superevent(event_or_superevent):
        # TODO: fix this
        query = Q()
    elif is_event(event_or_superevent):
        event = event_or_superevent
        query = Q(pipelines=event.pipeline) | Q(pipelines=None)

    # Iterate over triggers found from the label query
    # TODO: this doesn't work quite correctly since negated labels aren't
    # properly handled in the view function which creates triggers.
    # Example: a trigger with '~INJ' as the label_query has INJ in its labels
    # Idea: have filter_for_labels return a Q object generated from the
    #       label query
    triggers = label.trigger_set.filter(query).prefetch_related('contacts')
    for trigger in triggers:

        if len(trigger.label_query) > 0:
            qs_out = filter_for_labels(qs, trigger.label_query)

            # If the label query cleans out our query set, we'll continue
            # without adding the recipient.
            if not qs_out.exists():
                continue

        # Compile a list of recipients from the trigger's contacts.
        # Require that the user is in the LVC group as a safeguard
        contacts = trigger.contacts.filter(user__groups__name=
            settings.LVC_GROUP)
        email_recips |= contacts.exclude(email="").select_related('user')
        phone_recips |= contacts.exclude(phone="").select_related('user')

    return email_recips, phone_recips


def issue_alerts(event_or_superevent, alert_type, serialized_object,
    serialized_parent=None):

    # Send XMPP alert
    if settings.SEND_XMPP_ALERTS:
        issue_xmpp_alerts(event_or_superevent, alert_type, serialized_object,
            serialized_parent=serialized_parent)

    # Below here, we only do processing for email and phone alerts ------------
    if not (settings.SEND_EMAIL_ALERTS or settings.SEND_PHONE_ALERTS):
        return

    # TODO: make phone and e-mail alerts work for superevents
    if is_superevent(event_or_superevent):
        return

    # Phone and email alerts are currently only for "new" and "label_added"
    # alert_types, for events only.
    if (alert_type not in ['new', 'label_added']):
        return

    # Don't send phone or email alerts for MDC events or Test events
    if is_event(event_or_superevent):
        event = event_or_superevent
        if ((event.search and event.search.name == 'MDC') \
            or event.group.name == 'Test'):
            return

        # Don't send them for offline events, either
        if event.offline:
            return

    # Compile phone and email recipients for new or label alerts
    if alert_type not in ["new", "label"]:
        return

    if alert_type == "new":
        email_recips, phone_recips = get_alert_recips(event_or_superevent)
        # Force label = None for new alerts
        label = None
    elif alert_type == "label":
        email_recips, phone_recips = \
            get_alert_recips_for_label(event_or_superevent, label)

    if settings.SEND_EMAIL_ALERTS:
        url = reverse('view', args=[event_or_superevent.graceid])
        issue_email_alerts(event_or_superevent, url)

    if settings.SEND_PHONE_ALERTS and phone_recips:
        issue_phone_alerts(event_or_superevent, phone_recips, label=label)
