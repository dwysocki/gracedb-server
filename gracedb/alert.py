
import sys
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import EmailMessage
from django.conf import settings

import json

import logging
#from hashlib import sha1

#from ligo.overseer.client import send_to_overseer
#from multiprocessing import Process, Manager

log = logging.getLogger('gracedb.alert')

def issueAlert(event, location, event_url, serialized_object=None):
    issueXMPPAlert(event, location, serialized_object=serialized_object)
    issueEmailAlert(event, event_url)

def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    # XXX TBD what exactly this summary is.
    return "GPS Time: %s" % event.gpstime


# The serialized object passed in here will normally be an EventLog or EMBB log entry
def issueAlertForUpdate(event, description, doxmpp, filename="", serialized_object=None):
    if doxmpp:
        issueXMPPAlert(event, filename, "update", description, serialized_object)
    # XXX No emails for this.  Argh.

# The only kind of serialized object relevant for a Label is an event.
def issueAlertForLabel(event, label, doxmpp, serialized_event=None):
    if doxmpp:
        issueXMPPAlert(event, "", "label", label, serialized_event)
    # Email
    profileRecips = []
    pipeline = event.pipeline
    # Triggers on given label matching pipeline OR with no pipeline (wildcard type)
    triggers = label.trigger_set.filter(pipelines=pipeline)
    triggers = triggers | label.trigger_set.filter(pipelines=None)
    for trigger in triggers:
        for recip in trigger.contacts.all():
            profileRecips.append(recip.email)

    subject = "[gracedb] %s / %s / %s / %s" % (label.name, event.pipeline.name, event.search.name, event.graceid())

    message = "A %s event with graceid %s was labelled with %s" % \
              (event.pipeline.name, event.graceid(), label.name)

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


def issueEmailAlert(event, event_url):

    # Gather Recipients
    if event.group.name == 'Test':
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        bccaddresses = []
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = settings.ALERT_EMAIL_TO
        bccaddresses = settings.ALERT_EMAIL_BCC

        pipeline = event.pipeline
        triggers = pipeline.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
               if not trigger.farThresh:
                   bccaddresses.append(recip.email)
               else:
                   if event.far and event.far < trigger.farThresh:
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

    #send_mail(subject, message, fromaddress, toaddresses)

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

#    manager = Manager()

    for nodename in nodenames:
        
#        # Calculate unique message_id and log
#        message_id = sha1(nodename + msg).hexdigest()
#        log.info("issueXMPPAlert: sending %s to node %s" % (message_id, nodename))
#
#        rdict = manager.dict()
#        msg_dict = {'node_name': nodename, 'message': msg, 'action': 'push'}
#        p = Process(target=send_to_overseer, args=(msg_dict, rdict, log, True))
#        p.start()
#        p.join()
#
#        if rdict.get('success', None):
#            continue

        # If not success, we need to do this the old way.
        log.info("issueXMPPAlert: failover to lvalert_send") 
        null = open('/dev/null','w')
        p = Popen(
            ["lvalert_send",
             "--server=%s" % settings.ALERT_XMPP_SERVER,
             "--username=gracedb",
             "--password=w4k3upal1ve",
             "--file=-",
             "--node=%s" % nodename,
            ],
            executable="/usr/bin/lvalert_send",
            stdin=PIPE,
            stdout=null,
            stderr=STDOUT,
            env=env)

        out, err = p.communicate(msg)

        log.debug("issueXMPPAlert: return code %s" % p.returncode)
        if p.returncode > 0:
            # XXX This should probably raise an exception.
            log.debug("issueXMPPAlert: ERROR: %s" % err)

