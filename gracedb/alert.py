
import sys
import time
from subprocess import Popen, PIPE, STDOUT
import StringIO

from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, get_script_prefix

from gracedb.userprofile.models import Trigger, AnalysisType

import glue.ligolw.utils
import glue.lvalert.utils

XMPP_ALERT_CHANNELS = [
                        'burst_omega',
                        'test_omega',
                        'cbc_mbtaonline',
                        'test_mbtaonline',
                        'burst_cwb',
                        'test_cwb',
                      ]

def issueAlert(event, location, temp_data_loc):
    issueXMPPAlert(event, location, temp_data_loc)
    issueEmailAlert(event, location)

def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    # XXX TBD what exactly this summary is.
    return "GPS Time: %s" % event.gpstime


def issueEmailAlertForLabel(event, label):
    profileRecips = []
    atype = AnalysisType.objects.filter(code=event.analysisType)[0]
    triggers = label.trigger_set.filter(atypes=atype)
    for trigger in triggers:
        for recip in trigger.contacts.all():
            profileRecips.append(recip.email)

    subject = "[gracedb] %s / %s / %s" % (label.name, event.get_analysisType_display(), event.graceid())

    message = "A %s event with graceid %s was labelled with %s" % \
              (event.get_analysisType_display(), event.graceid(), label.name)

    if event.group.name == "Test":
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
        message += "\n\nWould have send email to: %s" % str(profileRecips)
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = profileRecips

    if toaddresses:
        email = EmailMessage(subject, message, fromaddress, toaddresses, [])
        email.send()


def issueEmailAlert(event, location):

    # Gather Recipients
    if event.group.name == 'Test':
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddresses = settings.ALERT_TEST_EMAIL_TO
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddresses = settings.ALERT_EMAIL_TO

        atype = AnalysisType.objects.filter(code=event.analysisType)[0]
        triggers = atype.trigger_set.filter(labels=None)
        for trigger in triggers:
            for recip in trigger.contacts.all():
                toaddresses.append(recip.email)

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

    email = EmailMessage(subject, message, fromaddress, toaddresses, [])
    email.send()

    #send_mail(subject, message, fromaddress, toaddresses)

def issueXMPPAlert(event, location, temp_data_loc):
    nodename = "%s_%s"% (event.group.name, event.get_analysisType_display())
    nodename = nodename.lower()

    # XXX awful!
    # Need a good way to know which things to send out to lvalert.
    # Currently, only MBTAOnline and Omega get alerts.
    if nodename not in XMPP_ALERT_CHANNELS:
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
        executable="/opt/lscsoft/glue/bin/lvalert_send",
        stdin=PIPE,
        stdout=null,
        stderr=STDOUT,
        env=env)

    #msg = createPayload(event.graceid(), location)
    xmldoc = glue.lvalert.utils.make_LVAlertTable(location, event.graceid(), temp_data_loc)
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

def createPayload (uid, filename):
    template = """<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE LIGO_LW SYSTEM "http://ldas-sw.ligo.caltech.edu/doc/ligolwAPI/html/ligolw_dtd.txt">
<LIGO_LW>
        <Table Name="LVAlert:table">
                <Column Type="lstring" Name="LVAlert:uid"/>
                <Column Type="lstring" Name="LVAlert:file"/>
                <Stream Name="LVAlert:table" Type="Local" Delimiter=",">
                        "%(uid)s","%(filename)s"
                </Stream>
        </Table>
</LIGO_LW>
"""
    return template % { 'uid': uid, 'filename': filename }

