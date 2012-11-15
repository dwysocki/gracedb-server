
import sys
import time
from subprocess import Popen, PIPE, STDOUT
import StringIO

from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, get_script_prefix

from userprofile.models import Trigger, AnalysisType

import glue.ligolw.utils
import glue.lvalert.utils

def issueAlert(event, location, temp_data_loc):
    issueXMPPAlert(event, location, temp_data_loc)
    issueEmailAlert(event, location)

def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    # XXX TBD what exactly this summary is.
    return "GPS Time: %s" % event.gpstime


def issueAlertForUpdate(event, description, doxmpp):
    if doxmpp:
        issueXMPPAlert(event, "", "", "update", description)
    # XXX No emails for this.  Argh.

def issueAlertForLabel(event, label, doxmpp):
    if doxmpp:
        issueXMPPAlert(event, "", "", "label", label)
    # Email
    profileRecips = []
    atype = AnalysisType.objects.filter(code=event.analysisType)[0]
    # Triggers on given label matching analysis type OR with no atype (wildcard type)
    triggers = label.trigger_set.filter(atypes=atype)
    triggers = triggers | label.trigger_set.filter(atypes=None)
    for trigger in triggers:
        for recip in trigger.contacts.all():
            profileRecips.append(recip.email)

    subject = "[gracedb] %s / %s / %s" % (label.name, event.get_analysisType_display(), event.graceid())

    message = "A %s event with graceid %s was labelled with %s" % \
              (event.get_analysisType_display(), event.graceid(), label.name)

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


def issueEmailAlert(event, location):

    # Gather Recipients
    if event.group.name == 'Test':
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        bccaddresses = []
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = settings.ALERT_EMAIL_TO
        bccaddresses = settings.ALERT_EMAIL_BCC

        atype = AnalysisType.objects.filter(code=event.analysisType)[0]
        triggers = atype.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
                bccaddresses.append(recip.email)

    subject = "[gracedb] %s event. ID: %s" % (event.get_analysisType_display(), event.graceid())
    message = """
New Event
%s / %s
GRACEID:   %s
Info:      %s
Data:      %s
TWiki:     %s
Submitter: %s
Event Summary:
%s
"""
    message %= (event.group.name,
                event.get_analysisType_display(),
                event.graceid(),
                'https://'+Site.objects.get_current().domain+ reverse("view", args=[event.graceid()]),
                event.weburl(),
                event.wikiurl(),
                event.submitter.name,
                indent(3, prepareSummary(event))
               )

    email = EmailMessage(subject, message, fromaddress, toaddresses, bccaddresses)
    email.send()

    #send_mail(subject, message, fromaddress, toaddresses)

def issueXMPPAlert(event, location, temp_data_loc, alert_type="new", description=""):
    nodename = "%s_%s"% (event.group.name, event.get_analysisType_display())
    nodename = nodename.lower()

    if nodename not in settings.XMPP_ALERT_CHANNELS:
        return

    env = {}
    env["PYTHONPATH"] = ":".join(sys.path)

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

    xmldoc = glue.lvalert.utils.make_LVAlertTable(
                    location,
                    event.graceid(),
                    temp_data_loc,
                    alert_type,
                    description)
    buf = StringIO.StringIO()
    glue.ligolw.utils.write_fileobj(xmldoc, buf)
    msg = buf.getvalue()

    p.stdin.write(msg)
    p.stdin.close()
    for i in range(1,10):
        res = p.poll()
        if res == None:
            time.sleep(1)
        else:
            break

