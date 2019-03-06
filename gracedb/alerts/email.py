from __future__ import absolute_import
import logging
import textwrap

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse

from core.time_utils import gpsToUtc
from core.urls import build_absolute_uri
from events.shortcuts import is_event

# Set up logger
logger = logging.getLogger(__name__)


EMAIL_SUBJECT = {
    'event': {
        'new': '[gracedb] {pipeline} event created: {graceid}',
        'update': '[gracedb] {pipeline} event updated: {graceid}',
        'label_added': \
            '[gracedb] {pipeline} event labeled with {label}: {graceid}',
        'label_removed': ('[gracedb] Label {label} removed from {pipeline} '
            'event: {graceid}'),
    },
    'superevent': {
        'new': '[gracedb] Superevent created: {sid}',
        'update': '[gracedb] Superevent updated: {sid}',
        'label_added': \
                '[gracedb] Superevent labeled with {label}: {sid}',
        'label_removed': \
                '[gracedb] Label {label} removed from superevent: {sid}',
    },
}

# es = 'Event' or 'Superevent'
# group_pipeline_ev_or_s = '{group} / {pipeline} event' or 'superevent'
EMAIL_BODY_TEMPLATE = textwrap.dedent("""\
    {alert_type_verb} {group_pipeline_ev_or_s}: {graceid}

        {es} time (GPS): {gpstime}
        {es} time (UTC): {utctime}
        {es} page: {detail_url}
        {es} data: {file_url}
        FAR: {far}
        Labels: {labels}
""").rstrip()

ALERT_TYPE_VERBS = {
    'new': 'New',
    'update': 'Updated',
    'label_added': 'Label {label} added to',
    'label_removed': 'Label {label} removed from',
}


def prepare_email_body(event_or_superevent, alert_type, label=None):

    # Sort out different cases for events or superevents
    if is_event(event_or_superevent):
        group_pipeline_ev_or_s = '{group} / {pipeline} event'.format(
            group=event_or_superevent.group.name,
            pipeline=event_or_superevent.pipeline.name)
        es = 'Event'
        detail_url = build_absolute_uri(reverse('view',
            args=[event_or_superevent.graceid]))
        file_url = build_absolute_uri(reverse('file_list',
            args=[event_or_superevent.graceid]))
    else:
        group_pipeline_ev_or_s = 'superevent'
        es = 'Superevent'
        detail_url = build_absolute_uri(reverse('superevents:view',
            args=[event_or_superevent.graceid]))
        file_url = build_absolute_uri(reverse('superevents:file-list',
            args=[event_or_superevent.graceid]))

    # Compile email body
    alert_type_verb = ALERT_TYPE_VERBS[alert_type]
    if label is not None and 'label' in alert_type:
        alert_type_verb = alert_type_verb.format(label=label.name)
    gpstime = event_or_superevent.gpstime
    labels = None
    if event_or_superevent.labels.exists():
        labels = ", ".join(event_or_superevent.labels.values_list(
            'name', flat=True))
    email_body = EMAIL_BODY_TEMPLATE.format(
        graceid=event_or_superevent.graceid,
        alert_type_verb=alert_type_verb,
        group_pipeline_ev_or_s=group_pipeline_ev_or_s,
        es=es,
        detail_url=detail_url,
        file_url=file_url,
        gpstime=gpstime,
        utctime=gpsToUtc(gpstime).isoformat(),
        far=event_or_superevent.far,
        labels=labels)

    # Add some extra information
    has_si = False
    if is_event(event_or_superevent):
        instruments = getattr(event_or_superevent, 'instruments', None)
        if instruments:
            email_body += '\n    Instruments: {inst}'.format(inst=instruments)
        if event_or_superevent.singleinspiral_set.exists():
            si = event_or_superevent.singleinspiral_set.first()
            has_si = True
    else:
        if event_or_superevent.preferred_event.singleinspiral_set.exists():
            si = event_or_superevent.preferred_event.singleinspiral_set.first()
            has_si = True
    if has_si:
        email_body += '\n    Component masses: {m1}, {m2}'.format(m1=si.mass1,
            m2=si.mass2)

    return email_body


def issue_email_alerts(event_or_superevent, alert_type, recipients,
    label=None):

    # Get subject template
    if is_event(event_or_superevent):
        event_type = 'event'
    else:
        event_type = 'superevent'
    subject_template = EMAIL_SUBJECT[event_type][alert_type]

    # Construct subject
    subj_kwargs = {}
    if label is not None and 'label' in alert_type:
        subj_kwargs['label'] = label.name
    if is_event(event_or_superevent):
        subj_kwargs['graceid'] = event_or_superevent.graceid
        subj_kwargs['pipeline'] = event_or_superevent.pipeline.name
    else:
        subj_kwargs['sid'] = event_or_superevent.superevent_id
    subject = subject_template.format(**subj_kwargs)

    # Get email body
    email_body = prepare_email_body(event_or_superevent, alert_type, label)

    # Log email recipients
    logger.debug("Sending email to {recips}".format(
        recips=", ".join([r.email for r in recipients])))

    # Send mail individually so all emails are not rejected due to a single
    # address being blacklisted
    for recip in recipients:
        # Send email
        email = EmailMessage(subject=subject, body=email_body,
            from_email=settings.ALERT_EMAIL_FROM, to=[recip.email])
        email.send()
