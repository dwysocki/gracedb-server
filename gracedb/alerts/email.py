from __future__ import absolute_import
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse

from core.time_utils import gpsToUtc
from core.urls import build_absolute_uri

# Set up logger
logger = logging.getLogger(__name__)

EMAIL_SUBJECT_NEW = "[gracedb] {pipeline} event. ID: {graceid}"
EMAIL_MESSAGE_NEW = """
New Event
{group} / {pipeline}
GRACEID:   {graceid}
Info:      {url}
Data:      {file_url}
Submitter: {submitter}
Event Summary:
{summary}
"""

EMAIL_SUBJECT_LABEL = "[gracedb] {label} / {pipeline} / {search} / {graceid}"
EMAIL_SUBJECT_LABEL_NOSEARCH = "[gracedb] {label} / {pipeline} / {graceid}"
EMAIL_MESSAGE_LABEL = """
A {pipeline} event with graceid {graceid} was labeled with {label}: {url}
"""


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


def issue_email_alerts(event, recips, label=None):

    # Prepare URLs for email message body
    event_url = build_absolute_uri(reverse("view", args=[event.graceid]))
    file_url = build_absolute_uri(reverse("file_list", args=[event.graceid]))

    # Compile subject and message content
    if label is None:
        # Alert for new event
        subject = EMAIL_SUBJECT_NEW.format(pipeline=event.pipeline.name,
            graceid=event.graceid)
        message = EMAIL_MESSAGE_NEW.format(group=event.group.name,
            pipeline=event.pipeline.name, graceid=event.graceid,
            url=event_url, file_url=file_url,
            submitter=event.submitter.get_full_name(),
            summary=indent(3, prepareSummary(event)))
    else:
        # Alert for label
        if event.search:
            subject = EMAIL_SUBJECT_LABEL.format(label=label.name,
                pipeline=event.pipeline.name, search=event.search.name,
                graceid=event.graceid)
        else:
            subject = EMAIL_SUBJECT_LABEL_NOSEARCH.format(label=label.name,
                pipeline=event.pipeline.name, graceid=event.graceid)
        message = EMAIL_MESSAGE_LABEL.format(pipeline=event.pipeline.name,
            graceid=event.graceid, label=label.name, url=event_url)

    # Actual recipients should be BCC'd
    bcc_addresses = [recip.email for recip in recips]

    # Compile from/to addresses
    from_address = settings.ALERT_EMAIL_FROM
    to_addresses = settings.ALERT_EMAIL_TO

    # Log email recipients
    logger.debug("Sending email to {recips}".format(
        recips=", ".join(bcc_addresses)))

    # Send email
    email = EmailMessage(subject, message, from_address, to_addresses,
        bcc_addresses)
    email.send()
