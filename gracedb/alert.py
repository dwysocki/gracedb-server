
import sys
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import Group

import json

import logging

from django_twilio.client import twilio_client

from utils import gpsToUtc

from query import filter_for_labels

from gracedb.models import Event

# These imports can be fragile, so they should be brought in only
# if use of the LVAlert overseer is really intended.
if settings.USE_LVALERT_OVERSEER:
    from hashlib import sha1
    from ligo.overseer.overseer_client import send_to_overseer
    from multiprocessing import Process, Manager

log = logging.getLogger('gracedb.alert')

def get_twilio_from():
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

    Note: twilio_recips is a list of users - we need phone numbers
          and group memberships for permission checks.
    """
    
    if (alert_type == "create"):
        # twiml_base_url is the URL of a TwiML Bin
        # (https://support.twilio.com/hc/en-us/articles/230878368)
        # with the following content:
        #
        #     <?xml version="1.0" encoding="UTF-8"?>
        #     <Response>
        #     <Say>
        #     A {{pipeline}} event with Grace DB ID {{graceid}} was created.
        #     </Say>
        #     <Sms>
        #     A {{pipeline}} event with GraceDB ID {{graceid}} was created.
        #     https://gracedb-test.ligo.org/events/view/{{graceid}}
        #     </Sms>
        #     </Response>
        twiml_base_url = 'https://handler.twilio.com/twiml/' + settings.TWILIO_CREATE_KEY
        twiml_url = '{0}?pipeline={1}&graceid={2}'.format(
            twiml_base_url, event.pipeline.name, event.graceid())
    elif (alert_type == "label"):
        # twiml_base_url is the URL of a TwiML Bin
        # (https://support.twilio.com/hc/en-us/articles/230878368)
        # with the following content:
        #
        #     <?xml version="1.0" encoding="UTF-8"?>
        #     <Response>
        #     <Say>
        #     A {{pipeline}} event with Grace DB ID {{graceid}} was labelled with {{label_lower}}.
        #     </Say>
        #     <Sms>
        #     A {{pipeline}} event with GraceDB ID {{graceid}} was labelled with {{label}}
        #     https://gracedb-test.ligo.org/events/view/{{graceid}}
        #     </Sms>
        #     </Response>
        twiml_base_url = 'https://handler.twilio.com/twiml/' + settings.TWILIO_LABEL_KEY
        label = kwargs['label']
        twiml_url = '{0}?pipeline={1}&graceid={2}&label={3}&label_lower={4}'.format(
            twiml_base_url, event.pipeline.name, event.graceid(), label.name, label.name.lower())
    else:
        log.exception('Failed to process alert_type in make_twilio_calls')

    # Get "from" phone number.
    from_ = get_twilio_from()
    
    # Get LVC user group for checks made below.
    lvc_group = Group.objects.get(name=settings.LVC_GROUP)
    
    # Loop over recipients and make calls.
    for recip in twilio_recips:
        try:
            # Only make calls to LVC members. Non-LVC members shouldn't
            # even be able to sign up with a phone number, but this is another
            # safety measure.
            if lvc_group in recip.user.groups.all():
                log.info('calling %s', recip.user.username)
                twilio_client.calls.create(recip.phone, from_, twiml_url, method='GET')
            else:
                log.info('user %s is not an LVC member, call not made' % recip.user.username)
        except:
            log.exception('Failed to create call')

def issueAlert(event, location, event_url, serialized_object=None):
    issueXMPPAlert(event, location, serialized_object=serialized_object)
    issueEmailAlert(event, event_url)

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
    # XXX No emails for this.  Argh.

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

    message = "A %s event with graceid %s was labelled with %s" % \
              (event.pipeline.name, event.graceid(), label.name)
    if event_url:
        message += '\n\n%s' % event_url

    if event.group.name == "Test":
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        bccaddresses = []
        message += "\n\nWould have send email to: %s" % str(profileRecips)
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses =  []
        bccaddresses = profileRecips

    if toaddresses or bccaddresses:
        if not toaddresses:
            toaddresses = ["(undisclosed recipients)"]
        email = EmailMessage(subject, message, fromaddress, toaddresses, bccaddresses)
        email.send()

    # Make phone calls.
    make_twilio_calls(event, phoneRecips, "label", label=label)

def issueEmailAlert(event, event_url):

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
        twilio_recips = []
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = settings.ALERT_EMAIL_TO
        # XXX Bizarrely, this settings.ALERT_EMAIL_BCC seems to be overwritten in a 
        # persistent way between calls, so that you can get alerts going out to the 
        # wrong contacts. I find that it works if you just start with an empty list
        # See: https://bugs.ligo.org/redmine/issues/2185
        #bccaddresses = settings.ALERT_EMAIL_BCC
        bccaddresses = []
        twilio_recips = []
        pipeline = event.pipeline
        triggers = pipeline.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
               if not trigger.farThresh:
                   if recip.email:
                       bccaddresses.append(recip.email)
                   if recip.phone:
                       twilio_recips.append(recip)
               else:
                   if event.far and event.far < trigger.farThresh:
                       if recip.email:
                           bccaddresses.append(recip.email)
                       if recip.phone:
                           twilio_recips.append(recip)
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

    # Make phone calls.
    make_twilio_calls(event, twilio_recips, "create")

def issueXMPPAlert(event, location, alert_type="new", description="", serialized_object=None):
    
    nodename = "%s_%s" % (event.group.name, event.pipeline.name)
    nodename = nodename.lower()
    nodenames = [ nodename, ]
    if event.search:
        nodename = nodename + "_%s" % event.search.name.lower()
        nodenames.append(nodename)

    log.debug('issueXMPPAlert: %s' % event.graceid())

# XXX We no longer check the XMPP_ALERT_CHANNELS list.
# If somebody sends an event, there should always be an alert.
# It is up to the end users to filter these out as desired.
#
#    if nodename not in settings.XMPP_ALERT_CHANNELS:
#        log.debug("issueXMPPAlert: did not send alert")
#        return

    env = {}
    env["PYTHONPATH"] = ":".join(sys.path)
    # Create the output dictionary and serialize as JSON.
    lva_data = {
        'file': location,
        'uid': event.graceid(),
        'alert_type': alert_type,
        # The following string cast is necessary because sometimes 
        # description is a label object!
        'description': str(description),
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

            null = open('/dev/null','w')
            p = Popen(
                ["lvalert_send",
                 #"--server=%s" % settings.ALERT_XMPP_SERVER,
                 "--server=%s" % server,
                 "--username=gracedb",
                 "--password=w4k3upal1ve",
                 "--file=-",
                 "--node=%s" % nodename,
                ],
                #executable="/usr/bin/lvalert_send",
                executable=settings.LVALERT_SEND_EXECUTABLE,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                env=env)

            out, err = p.communicate(msg)

            log.debug("issueXMPPAlert: return code %s" % p.returncode)
            if p.returncode > 0:
                # XXX This should probably raise an exception.
                log.debug("issueXMPPAlert: ERROR: %s" % err)

