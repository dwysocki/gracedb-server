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

from core.time_utils import gpsToUtc
from events.models import Event
from events.permission_utils import is_external
from events.query import filter_for_labels
from events.shortcuts import is_event
from superevents.shortcuts import is_superevent
from .xmpp import issue_xmpp_alert

# Set up logger
log = logging.getLogger(__name__)


def check_recips(recips_qs):
    """
    Make sure only internal users are included. Assumes that the queryset's
    model has a foreign key to the user object.
    """
    LVC_GROUP = Group.objects.get(name=settings.LVC_GROUP)
    return recips_qs.filter(user__groups=LVC_GROUP)


def get_alert_recips(event_or_superevent):

    if is_superevent(event_or_superevent):
        # TODO: update for superevents
        pass
    elif is_event(event_or_superevent):
        event = event_or_superevent
        triggers = event.pipeline.trigger_set.filter(labels=None) \
            .prefetch_related('contacts')
        email_recips = [c for t in triggers for c in
            t.contacts.all().select_related('user')
            if ((not t.farThresh or (event.far and event.far < t.farThresh))
            and r.email)]
        phone_recips = [c for t in triggers for c in
            t.contacts.all().select_related('user')
            if ((not t.farThresh or (event.far and event.far < t.farThresh))
            and r.phone)]

    return check_recips(email_recips), check_recips(phone_recips)


def get_alert_recips_for_label(event_or_superevent, label):
    # Blank QuerySets for recipients
    email_recips = QuerySet()
    phone_recips = QuerySet()

    # Construct a queryset containing only this object; needed for
    # call to filter_for_labels
    qs = event_or_superevent.model.objects.filter(id=event_or_superevent.id)

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
    for trigger in triggers.related():

        if len(trigger.label_query) > 0:
            qs_out = filter_for_labels(qs, trigger.label_query)

            # If the label query cleans out our query set, we'll continue
            # without adding the recipient.
            if not qs_out.exists():
                continue

        # Compile a list of recipients from the trigger's contacts
        email_recips |= trigger.contacts.exclude(email="") \
            .select_related('user')
        phone_recips |= trigger.contacts.exclude(phone="") \
            .select_related('user')
        #email_recips.extend([c for c in
        #    trigger.contacts.all().select_related('user') if c.email])
        #phone_recips.extend([c for c in
        #    trigger.contacts.all().select_related('user') if c.phone])

    return check_recips(email_recips), check_recips(phone_recips)


def issue_alerts(event_or_superevent, alert_type, url=None, file_name="",
    description="", label=None, serialized_object=None):

    # Check alert_type
    if alert_type not in ["new", "label", "update", "signoff"]:
        raise ValueError(("alert_type is {0}, should be 'new', 'label', "
            "'update', or 'signoff'").format(alert_type))

    # Send XMPP alert
    if settings.SEND_XMPP_ALERTS:
        issue_xmpp_alert(event_or_superevent, alert_type, file_name,
            description=description, serialized_object=serialized_object)

    # Below here, we only do processing for email and phone alerts ------------

    # TODO: make phone and e-mail alerts work for superevents
    if is_superevent(event_or_superevent):
        return

    # We currently don't send phone or email alerts for updates or signoffs
    if alert_type == "update" or alert_type == "signoff":
        return

    # Don't send phone or email alerts for MDC events or Test events
    if is_event(event_or_superevent):
        event = event_or_superevent
        if ((event.search and event.search.name == 'MDC') \
            or event.group.name == 'Test'):
            return

    # Compile phone and email recipients for alert
    if alert_type == "new":
        email_recips, phone_recips = get_alert_recips(event_or_superevent)
        # Force label = None for new alerts
        label = None
    elif alert_type == "label":
        email_recips, phone_recips = \
            get_alert_recips_for_label(event_or_superevent, label)

    if settings.SEND_EMAIL_ALERTS:
        issueEmailAlert(event_or_superevent, url)

    if settings.SEND_PHONE_ALERTS and phone_recips:
        issue_phone_alerts(event_or_superevent, phone_recips, label=label)
