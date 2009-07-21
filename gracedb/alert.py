
import sys
import time
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, get_script_prefix


def issueAlert(event, location):
    issueXMPPAlert(event, location)
    issueEmailAlert(event, location)

def indent(nindent, text):
    return "\n".join([(nindent*' ')+line for line in text.split('\n')])

def prepareSummary(event):
    # XXX TBD what exactly this summary is.
    return "GPS Time: %s" % event.gpstime

def issueEmailAlert(event, location):
    if event.group.name == 'Test':
        fromaddress = settings.ALERT_TEST_EMAIL_FROM
        toaddress = settings.ALERT_TEST_EMAIL_TO
    else:
        fromaddress = settings.ALERT_EMAIL_FROM
        toaddress = settings.ALERT_EMAIL_TO
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
                indent(3, prepareSummary(event)))
    send_mail(subject, message, fromaddress, toaddress)

def issueXMPPAlert(event, location):
    # XXX awful!
    # Need a good way to know which things to send out to lvalert.
    # Currently, only Test/* and CBC/MBTAOnline get alerts.
    if event.analysisType != 'MBTA' and event.group.name != 'Test':
        return

    env = {}
    env["PYTHONPATH"] = ":".join(sys.path)

    nodename = "%s_%s"% (event.group.name, event.get_analysisType_display())
    nodename = nodename.lower()

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
    msg = createPayload(event.graceid(), location)
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

