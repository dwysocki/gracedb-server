
import os
import sys
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import EmailMessage
from django.conf import settings

from permission_utils import is_external

import json

import logging
log = logging.getLogger(__name__)

from django_twilio.client import twilio_client

from core.time_utils import gpsToUtc

from query import filter_for_labels

from gracedb.models import Event

import socket

# These imports can be fragile, so they should be brought in only
# if use of the LVAlert overseer is really intended.
if settings.USE_LVALERT_OVERSEER:
    from hashlib import sha1
    from ligo.overseer.overseer_client import send_to_overseer
    from multiprocessing import Process, Manager

# Dict for managing TwiML bin arguments.
# Should match structure of TWIML_BINS dict in
# settings/secret_settings.py.
TWIML_ARG_STR = {
    'create': 'pipeline={0}&graceid={1}&server={2}',
    'label': 'pipeline={0}&graceid={1}&label_lower={2}&server={3}',
}

# Dict for managing Twilio message contents.
TWILIO_MSG_CONTENT = {
    'create': ('A {pipeline} event with GraceDB ID {graceid} was created.'
               ' https://{server}.ligo.org/events/view/{graceid}'),
    'label': ('A {pipeline} event with GraceDB ID {graceid} was labeled with '
              '{label}. https://{server}.ligo.org/events/view/{graceid}')
}

def get_twilio_from():
    """Gets phone number which Twilio alerts come from."""
    for from_ in twilio_client.phone_numbers.iter():
        return from_.phone_number
    raise RuntimeError('Could not determine "from" Twilio phone number')

def make_twilio_calls(event, twilio_recips, alert_type, **kwargs):
    """
    USAGE:
    ------
        New event created:
            make_twilio_calls(event, twilio_recips, "create")
        New label applied to event (Label is a GraceDB model):
            make_twilio_calls(event, twilio_recips, "label", label=Label)

    Note: twilio_recips is a list of User objects.
    """
    # Get server name.
    hostname = socket.gethostname()

    # Get "from" phone number.
    from_ = get_twilio_from()

    # Compile voice URL and text message body for given alert type.
    if (alert_type == "create"):
        twiml_url = settings.TWIML_BASE_URL + \
            settings.TWIML_BIN[alert_type] + "?" + \
            TWIML_ARG_STR[alert_type].format(event.pipeline.name,
                event.graceid(), hostname)
        msg_body = TWILIO_MSG_CONTENT[alert_type].format(
            pipeline=event.pipeline.name, graceid=event.graceid(),
            server=hostname)
    elif (alert_type == "label"):
        twiml_url = settings.TWIML_BASE_URL + \
            settings.TWIML_BIN[alert_type] + "?" + \
            TWIML_ARG_STR[alert_type].format(event.pipeline.name,
                event.graceid(), kwargs["label"].name.lower(), hostname)
        msg_body = TWILIO_MSG_CONTENT[alert_type].format(
            pipeline=event.pipeline.name, graceid=event.graceid(),
            label=kwargs["label"].name, server=hostname)
    else:
        log.exception("Failed to process alert_type {0}".format(alert_type))

    # Loop over recipients and make calls and/or texts.
    for recip in twilio_recips:
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
                log.debug("Calling {0} at {1}" \
                          .format(recip.user.username, recip.phone))
                twilio_client.calls.create(to=recip.phone, from_=from_,
                    url=twiml_url, method='GET')

            # Create Twilio message.
            if recip.text_phone:
                log.debug("Texting {0} at {1}" \
                          .format(recip.user.username, recip.phone))
                twilio_client.messages.create(to=recip.phone, from_=from_,
                    body=msg_body)
        except:
            log.exception("Failed to contact {0} at {1}." \
                          .format(recip.user.username, recip.phone))

def issueAlert(event, location, event_url, serialized_object=None):
    issueXMPPAlert(event, location, serialized_object=serialized_object)
    issueEmailAlert(event, event_url)
    issuePhoneAlert(event)

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

# The serialized object passed in here will normally be an EventLog or EMBB log entry
def issueAlertForUpdate(event, description, doxmpp, filename="", serialized_object=None):
    if doxmpp:
        issueXMPPAlert(event, filename, "update", description, serialized_object)
    # XXX No emails or phone calls for this.  Argh.

# The only kind of serialized object relevant for a Label is an event.
def issueAlertForLabel(event, label, doxmpp, serialized_event=None, event_url=None):
    if doxmpp:
        issueXMPPAlert(event, "", "label", label, serialized_event)
    # Email
    profileRecips = []
    phoneRecips = []
    pipeline = event.pipeline
    # Triggers on given label matching pipeline OR with no pipeline (wildcard type)
    triggers = label.trigger_set.filter(pipelines=pipeline)
    triggers = triggers | label.trigger_set.filter(pipelines=None)
    for trigger in triggers:
        if len(trigger.label_query) > 0:
            # construct a queryset containing only this event
            qs = Event.objects.filter(id=event.id)
            qs = filter_for_labels(qs, trigger.label_query)
            # If the label query cleans out our query set, we'll continue
            # without adding the recipient.
            if qs.count() == 0:
                continue

        for recip in trigger.contacts.all():
            if recip.email:
                profileRecips.append(recip.email)
            if recip.phone:
                phoneRecips.append(recip)

    if event.search:
        subject = "[gracedb] %s / %s / %s / %s" % (label.name, event.pipeline.name, event.search.name, event.graceid())
    else:
        subject = "[gracedb] %s / %s / %s" % (label.name, event.pipeline.name, event.graceid())

    message = "A %s event with graceid %s was labeled with %s" % \
              (event.pipeline.name, event.graceid(), label.name)
    if event_url:
        message += '\n\n%s' % event_url

    if event.group.name == "Test":
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        bccaddresses = []
        message += "\n\nWould have sent email to: %s" % str(profileRecips)
        message += "\n\nWould have called/texted: {0}" \
            .format(str([c.phone for c in phoneRecips]))
        phoneRecips = []
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses =  []
        bccaddresses = profileRecips

    if settings.SEND_EMAIL_ALERTS and (toaddresses or bccaddresses):
        if not toaddresses:
            toaddresses = ["(undisclosed recipients)"]
        email = EmailMessage(subject, message, fromaddress, toaddresses, bccaddresses)
        email.send()

    # Make phone calls.
    if settings.SEND_PHONE_ALERTS and phoneRecips:
        make_twilio_calls(event, phoneRecips, "label", label=label)

def issueEmailAlert(event, event_url):

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

    subject = "[gracedb] %s event. ID: %s" % (event.pipeline.name, event.graceid())
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
                event.graceid(),
                event_url,
                event.weburl(),
                "%s %s" % (event.submitter.first_name, event.submitter.last_name),
                indent(3, prepareSummary(event))
               )

    email = EmailMessage(subject, message, fromaddress, toaddresses, bccaddresses)
    email.send()

def issuePhoneAlert(event):

    # Check settings switch for turning off phone alerts
    if not settings.SEND_PHONE_ALERTS:
        return

    # The right way of doing this is to make the email alerts filter-able
    # by search. But this is a low priority dev task. For now, we simply 
    # short-circuit in case this is an MDC event.
    if event.search and event.search.name == 'MDC':
        return

    # Gather recipients
    phoneRecips = []
    if event.group.name != 'Test':
        pipeline = event.pipeline
        triggers = pipeline.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
                if ((event.far and event.far < trigger.farThresh)
                    or not trigger.farThresh):
                    if recip.phone:
                        phoneRecips.append(recip)

    # Make phone calls.
    if phoneRecips:
        make_twilio_calls(event, phoneRecips, "create")

def issueXMPPAlert(event, location, alert_type="new", description="", serialized_object=None):
    
    # Check settings switch for turning off XMPP alerts
    if not settings.SEND_XMPP_ALERTS:
        return

    nodename = "%s_%s" % (event.group.name, event.pipeline.name)
    nodename = nodename.lower()
    nodenames = [ nodename, ]
    if event.search:
        nodename = nodename + "_%s" % event.search.name.lower()
        nodenames.append(nodename)

    log.debug('issueXMPPAlert: %s' % event.graceid())

    # Create the output dictionary and serialize as JSON.
    lva_data = {
        'file': location,
        'uid': event.graceid(),
        'alert_type': alert_type,
        # The following string cast is necessary because sometimes 
        # description is a label object!
        'description': str(description),
        'labels': [label.name for label in event.labels.all()]
    }
    if serialized_object:
        lva_data['object'] = serialized_object
    msg = json.dumps(lva_data)
    log.debug("issueXMPPAlert: writing message %s" % msg)

    if settings.USE_LVALERT_OVERSEER:
        manager = Manager()

    for server in settings.ALERT_XMPP_SERVERS:
        port = settings.LVALERT_OVERSEER_PORTS[server]
        for nodename in nodenames:
            
            if settings.USE_LVALERT_OVERSEER:
                # Calculate unique message_id and log
                message_id = sha1(nodename + msg).hexdigest()
                log.info("issueXMPPAlert: sending %s,%s,%s to node %s" % (event.graceid(), alert_type, message_id, nodename))

                rdict = manager.dict()
                msg_dict = {'node_name': nodename, 'message': msg, 'action': 'push'}
                p = Process(target=send_to_overseer, args=(msg_dict, rdict, log, True, port))
                p.start()
                p.join()

                if rdict.get('success', None):
                    continue

                # If not success, we need to do this the old way.
                log.info("issueXMPPAlert: failover to lvalert_send") 
            else:
                # Not using LVAlert overseer, so just log the node and server
                log.info("issueXMPPAlert: sending to node %s on %s" % (nodename, server))

            # Set up environment for running lvalert_send script
            env = os.environ.copy()

            # Construct lvalert_send command
            p = Popen(
                ["lvalert_send",
                 "--server=%s" % server,
                 "--file=-",
                 "--node=%s" % nodename,
                ],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=env)

            # Send lvalert message to subprocess
            out, err = p.communicate(msg)

            log.debug("issueXMPPAlert: lvalert_send: return code %s" % p.returncode)
            if p.returncode > 0:
                # XXX This should probably raise an exception.
                log.error("issueXMPPAlert: ERROR: %s" % err)

