from __future__ import absolute_import
import logging

from django.core.mail import EmailMessage
from django.conf import settings

from core.time_utils import gpsToUtc

# Set up logger
log = logging.getLogger(__name__)


def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    gpstime = event.gpstime
    utctime = gpsToUtc(gpstime).strftime("%Y-%m-%d %H:%M:%S")
    instruments = getattr(event, 'instruments', "")
    far = getattr(event, 'far', 1.0)
    summary_template = """
    Event Time (GPS): %s 
    Event Time (UTC): %s
    Instruments: %s 
    FAR: %.3E """
    summary = summary_template % (gpstime, utctime, instruments, far)
    si_set = event.singleinspiral_set.all()
    if si_set.count():
        si = si_set[0]
        summary += """
    Component masses: %.2f, %.2f """ % (si.mass1, si.mass2)
    return summary

def issue_email_alerts(event, event_url):

    # Check settings switch for turning off email alerts
    if not settings.SEND_EMAIL_ALERTS:
        return

    # The right way of doing this is to make the email alerts filter-able
    # by search. But this is a low priority dev task. For now, we simply 
    # short-circuit in case this is an MDC event.
    if event.search and event.search.name == 'MDC':
        return

    # Gather Recipients
    if event.group.name == 'Test':
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        bccaddresses = []
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = settings.ALERT_EMAIL_TO
        # XXX Bizarrely, this settings.ALERT_EMAIL_BCC seems to be overwritten in a 
        # persistent way between calls, so that you can get alerts going out to the 
        # wrong contacts. I find that it works if you just start with an empty list
        # See: https://bugs.ligo.org/redmine/issues/2185
        #bccaddresses = settings.ALERT_EMAIL_BCC
        bccaddresses = []
        pipeline = event.pipeline
        triggers = pipeline.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
                if ((event.far and event.far < trigger.farThresh)
                    or not trigger.farThresh):
                    if recip.email:
                        bccaddresses.append(recip.email)

    subject = "[gracedb] %s event. ID: %s" % (event.pipeline.name, event.graceid)
    message = """
New Event
%s / %s
GRACEID:   %s
Info:      %s
Data:      %s
Submitter: %s
Event Summary:
%s
"""
    message %= (event.group.name,
                event.pipeline.name,
                event.graceid,
                event_url,
                event.weburl(),
                "%s %s" % (event.submitter.first_name, event.submitter.last_name),
                indent(3, prepareSummary(event))
               )

    email = EmailMessage(subject, message, fromaddress, toaddresses, bccaddresses)
    email.send()
