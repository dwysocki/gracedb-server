from __future__ import absolute_import
import logging
import socket

from django.conf import settings
from django_twilio.client import twilio_client
from events.permission_utils import is_external

# Set up logger
logger = logging.getLogger(__name__)


# TODO: generalize to superevents
# Dict for managing TwiML bin arguments.
# Should match structure of TWIML_BINS dict in
# config/settings/secret.py.
TWIML_ARG_STR = {
    'new': 'pipeline={pipeline}&graceid={graceid}&server={server}',
    'label_added': ('pipeline={pipeline}&graceid={graceid}&label_lower={label}'
              '&server={server}'),
}

# TODO: fix these by using reverse
# Dict for managing Twilio message contents.
TWILIO_MSG_CONTENT = {
    'new': ('A {pipeline} event with GraceDB ID {graceid} was created.'
               ' https://{server}.ligo.org/events/view/{graceid}'),
    'label_added': ('A {pipeline} event with GraceDB ID {graceid} was labeled '
              'with {label}. https://{server}.ligo.org/events/view/{graceid}')
}


def get_twilio_from():
    """Gets phone number which Twilio alerts come from."""
    for from_ in twilio_client.incoming_phone_numbers.list():
        return from_.phone_number
    raise RuntimeError('Could not determine "from" Twilio phone number')


def issue_phone_alerts(event, contacts, label=None):
    """
    USAGE:
    ------
        New event created:
            issue_phone_alerts(event, contacts)
        New label applied to event (Label is a GraceDB model):
            issue_phone_alerts(event, contacts, label=Label)

    Note: contacts is a QuerySet of Contact objects.
    """

    # Determine alert_type
    if label is not None:
        alert_type = "label_added"
    else:
        alert_type = "new"

    # Get server name.
    hostname = socket.gethostname()

    # Get "from" phone number.
    from_ = get_twilio_from()

    # Compile Twilio voice URL and message body
    msg_params = {
        'pipeline': event.pipeline.name,
        'graceid': event.graceid,
        'server': hostname,
    }
    if alert_type == "label_added":
        msg_params['label'] = label.name
    twiml_url = settings.TWIML_BASE_URL + settings.TWIML_BIN[alert_type] + \
        "?" + TWIML_ARG_STR[alert_type]
    twiml_url = twiml_url.format(**msg_params)
    msg_body = TWILIO_MSG_CONTENT[alert_type].format(**msg_params)

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
            # POST to TwiML bin to make voice call.
            if contact.call_phone:
                logger.debug("Calling {0} at {1}".format(contact.user.username,
                    contact.phone))
                twilio_client.calls.create(to=contact.phone, from_=from_,
                    url=twiml_url, method='GET')

            # Create Twilio message.
            if contact.text_phone:
                logger.debug("Texting {0} at {1}".format(contact.user.username,
                    contact.phone))
                twilio_client.messages.create(to=contact.phone, from_=from_,
                    body=msg_body)
        except Exception as e:
            logger.exception("Failed to contact {0} at {1}.".format(
                contact.user.username, contact.phone))
