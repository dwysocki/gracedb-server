from __future__ import absolute_import
import logging

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode

from django_twilio.client import twilio_client

from core.urls import build_absolute_uri
from events.permission_utils import is_external
from events.shortcuts import is_event
from . import egad
from .utils import convert_superevent_id_to_speech


# Set up logger
logger = logging.getLogger(__name__)


# Dict for managing Twilio message contents.
TWILIO_MSG_CONTENT = {
    'event': {
        'new': ('A {pipeline} event with GraceDB ID {graceid} was created. '
            '{url}'),
        'update': ('A {pipeline} event with GraceDB ID {graceid} was updated. '
            '{url}'),
        'label_added': ('A {pipeline} event with GraceDB ID {graceid} was '
              'labeled with {label}. {url}'),
        'label_removed': ('The label {label} was removed from a {pipeline} '
            'event with GraceDB ID {graceid}. {url}'),
    },
    'superevent': {
        'new': 'A superevent with GraceDB ID {sid} was created. {url}',
        'update': 'A superevent with GraceDB ID {sid} was updated. {url}',
        'label_added': ('A superevent with GraceDB ID {sid} was labeled with '
            '{label}. {url}'),
        'label_removed': ('The label {label} was removed from a superevent '
            'with GraceDB ID {sid}. {url}'),
    },
}


def get_twilio_from():
    """Gets phone number which Twilio alerts come from."""
    for from_ in twilio_client.incoming_phone_numbers.list():
        return from_.phone_number
    raise RuntimeError('Could not determine "from" Twilio phone number')


def get_message_content(event_or_superevent, alert_type, **kwargs):
    """Get content for text messages"""
    # kwargs should include 'label' for label_added and label_removed alerts

    # Get template
    if is_event(event_or_superevent):
        event_type = 'event'
    else:
        event_type = 'superevent'
    msg_template = TWILIO_MSG_CONTENT[event_type][alert_type]

    # Compile message content
    if is_event(event_or_superevent):
        event = event_or_superevent
        # Get url
        url = build_absolute_uri(reverse('view', args=[event.graceid]))

        # Compile message
        msg = msg_template.format(graceid=event.graceid,
            pipeline=event.pipeline.name, url=url, **kwargs)
    else:
        superevent = event_or_superevent
        # get url
        url = build_absolute_uri(reverse('superevents:view',
            args=[superevent.superevent_id]))

        # Compile message
        msg = msg_template.format(sid=superevent.superevent_id, url=url,
            **kwargs)

    return msg


def compile_twiml_url(event_or_superevent, alert_type, **kwargs):
    # Try to get label from kwargs - should be a string corresponding
    # to the label name here
    label = kwargs.get('label', None)

    # Compile urlparams
    if is_event(event_or_superevent):
        urlparams = {
            'graceid': event_or_superevent.graceid,
            'pipeline': event_or_superevent.pipeline.name,
        }
        twiml_bin_dict = settings.TWIML_BIN['event']
    else:
        urlparams = {'sid': convert_superevent_id_to_speech(
            event_or_superevent.superevent_id)}
        twiml_bin_dict = settings.TWIML_BIN['superevent']
    if label is not None:
        urlparams['label_lower'] = label.lower()

    # Construct TwiML URL
    twiml_url = '{base}{twiml_bin}?{params}'.format(
        base=settings.TWIML_BASE_URL,
        twiml_bin=twiml_bin_dict[alert_type],
        params=urlencode(urlparams))

    return twiml_url


## OLD VERSION ##
def issue_phone_alerts(event_or_superevent, alert_type, contacts, label=None):
    """
    Note: contacts is a QuerySet of Contact objects.
    """
    # Get "from" phone number.
    from_ = get_twilio_from()

    # Get message content
    msg_kwargs = {}
    if alert_type in ['label_added', 'label_removed'] and label:
        msg_kwargs['label'] = label.name
    msg_body = get_message_content(event_or_superevent, alert_type,
        **msg_kwargs)

    # Compile Twilio voice URL
    twiml_url = compile_twiml_url(event_or_superevent, alert_type,
        **msg_kwargs)

    # Loop over recipients and make calls and/or texts.
    for contact in contacts:
        if is_external(contact.user):
            # Only make calls to LVC members (non-LVC members
            # shouldn't even be able to sign up for phone alerts,
            # but this is another safety measure.
            logger.warning("External user {0} is somehow signed up for"
                " phone alerts".format(contact.user.username))
            continue

        try:
            if (contact.phone_method in [contact.__class__.CONTACT_PHONE_CALL,
                contact.__class__.CONTACT_PHONE_BOTH]):
                # POST to TwiML bin to make voice call.
                logger.debug("Calling {0} at {1}".format(contact.user.username,
                    contact.phone))
                twilio_client.calls.create(to=contact.phone, from_=from_,
                    url=twiml_url, method='GET')
        except Exception as e:
            logger.exception("Failed to call {0} at {1}.".format(
                contact.user.username, contact.phone))

        try:
            # Create Twilio message.
            if (contact.phone_method in [contact.__class__.CONTACT_PHONE_TEXT,
                contact.__class__.CONTACT_PHONE_BOTH]):
                logger.debug("Texting {0} at {1}".format(contact.user.username,
                    contact.phone))
                twilio_client.messages.create(to=contact.phone, from_=from_,
                    body=msg_body)
        except Exception as e:
            logger.exception("Failed to text {0} at {1}.".format(
                contact.user.username, contact.phone))


def issue_phone_alerts(event_or_superevent, alert_type, contacts, label=None):
    # Get message content
    msg_kwargs = {}
    if alert_type in ['label_added', 'label_removed'] and label:
        msg_kwargs['label'] = label.name
    message = get_message_content(event_or_superevent, alert_type,
        **msg_kwargs)

    # Compile Twilio voice URL
    twiml_url = compile_twiml_url(event_or_superevent, alert_type,
        **msg_kwargs)

    # Loop over recipients to get information needed by EGAD
    contacts_info = []
    for contact in contacts:
        if is_external(contact.user):
            # Only make calls to LVC members (non-LVC members
            # shouldn't even be able to sign up for phone alerts,
            # but this is another safety measure.
            logger.warning("External user {0} is somehow signed up for"
                " phone alerts".format(contact.user.username))
            continue

        contacts_info.append({
            "phone_method": contact.phone_method,
            "phone_number": contact.phone,
        })

    payload = {
        "contacts": contacts_info,
        "message": message,
        "twiml_url": twiml_url,
    }

    egad.send_alert("phone", payload)
