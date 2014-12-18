
import sys
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import EmailMessage
from django.conf import settings

import json

import logging

log = logging.getLogger('gracedb.alert')

def issueAlert(event, location, temp_data_loc, event_url):
    issueXMPPAlert(event, location, temp_data_loc)
    issueEmailAlert(event, event_url)

def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    # XXX TBD what exactly this summary is.
    return "GPS Time: %s" % event.gpstime


def issueAlertForUpdate(event, description, doxmpp, filename=""):
    if doxmpp:
        issueXMPPAlert(event, filename, "", "update", description)
    # XXX No emails for this.  Argh.

def issueAlertForLabel(event, label, doxmpp):
    if doxmpp:
        issueXMPPAlert(event, "", "", "label", label)
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

def issueXMPPAlert(event, location, temp_data_loc, alert_type="new", description=""):
    
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
        'data_loc': temp_data_loc,
        'alert_type': alert_type,
        # The following string cast is necessary because sometimes 
        # description is a label object!
        'description': str(description),
    }
    msg = json.dumps(lva_data)
    log.debug("issueXMPPAlert: writing message %s" % msg)

    for nodename in nodenames:
        log.debug("issueXMPPAlert: attempting to send alert to node %s" % nodename)
        null = open('/dev/null','w')
        p = Popen(
            ["lvalert_send",
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

