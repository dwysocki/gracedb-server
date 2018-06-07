import socket

from django.conf import settings
from django_twilio.client import twilio_client
from events.permission_utils import is_external

import logging
log = logging.getLogger(__name__)


# TODO: generalize to superevents
# Dict for managing TwiML bin arguments.
# Should match structure of TWIML_BINS dict in
# config/settings/secret.py.
TWIML_ARG_STR = {
    'new': 'pipeline={pipeline}&graceid={graceid}&server={server}',
    'label': ('pipeline={pipeline}&graceid={graceid}&label_lower={label}'
              '&server={server}'),
}

# TODO: fix these by using reverse
# Dict for managing Twilio message contents.
TWILIO_MSG_CONTENT = {
    'new': ('A {pipeline} event with GraceDB ID {graceid} was created.'
               ' https://{server}.ligo.org/events/view/{graceid}'),
    'label': ('A {pipeline} event with GraceDB ID {graceid} was labeled with '
              '{label}. https://{server}.ligo.org/events/view/{graceid}')
}


def get_twilio_from():
    """Gets phone number which Twilio alerts come from."""
    for from_ in twilio_client.phone_numbers.iter():
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
        alert_type = "label"
    else:
        alert_type = "new"

    # Get server name.
    hostname = socket.gethostname()

    # Get "from" phone number.
    from_ = get_twilio_from()

    # Compile Twilio voice URL and message body
    msg_params = {
        'pipeline': event.pipeline.name,
        'graceid': event.graceid(),
        'server': hostname,
    }
    if alert_type == "label";
        msg_params['label'] = label.name
    twiml_url = settings.TWIML_BASE_URL + settings.TWIML_BIN[alert_type] + \
        "?" + TWIML_ARG_STR[alert_type]
    twiml_url = twiml_url.format(**msg_params)
    msg_body = TWILIO_MSG_CONTENT[alert_type].format(**msg_params)

    # Loop over recipients and make calls and/or texts.
    for contact in twilio_recips:
        if is_external(recip.user):
            # Only make calls to LVC members (non-LVC members
            # shouldn't even be able to sign up for phone alerts,
            # but this is another safety measure.
            log.warning("External user {0} is somehow signed up for"
                        " phone alerts".format(recip.user.username))
            continue

        try:
            # POST to TwiML bin to make voice call.
            if recip.call_phone:
                log.debug("Calling {0} at {1}".format(recip.user.username,
                    recip.phone))
                twilio_client.calls.create(to=recip.phone, from_=from_,
                    url=twiml_url, method='GET')

            # Create Twilio message.
            if recip.text_phone:
                log.debug("Texting {0} at {1}".format(recip.user.username,
                    recip.phone))
                twilio_client.messages.create(to=recip.phone, from_=from_,
                    body=msg_body)
        except Exception as e:
            log.exception("Failed to contact {0} at {1}.".format(
                recip.user.username, recip.phone))


# TODO: update for superevents
def get_phone_recips(event):
    triggers = event.pipeline.trigger_set.filter(labels=None) \
        .prefetch_related('contacts')
    phone_recips = [c for t in triggers for c in
        t.contacts.all().select_related('user')
        if ((not t.farThresh or (event.far and event.far < t.farThresh)) and
        r.phone)]

    return phone_recips


