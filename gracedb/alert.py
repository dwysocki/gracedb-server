
import sys
import time
from subprocess import Popen, PIPE, STDOUT

from django.core.mail import send_mail
from django.conf import settings

def issueAlert(event, location):
    issueXMPPAlert(event, location)
    issueEmailAlert(event, location)

def issueEmailAlert(event, location):
    subject = "[gracedb] New %s event. ID: %s" % (event.get_analysisType_display(), event.graceid())
    message = """
    New Event
    %s / %s
    GRACEID:    %s
    Location:   %s
    TWiki Page: %s
"""
    message %= (event.group.name, event.get_analysisType_display(), event.graceid(), location, event.wikiurl())
    fromaddress = settings.ALERT_EMAIL_FROM
    to = settings.ALERT_EMAIL_TO
    send_mail(subject, message, fromaddress, to)

def issueXMPPAlert(event, location):
    # XXX awful!
    if event.analysisType != 'MBTA':
        return

    env = {}
    pythonpath = ":".join(sys.path)
    env["PYTHONPATH"] = pythonpath
    null = open('/dev/null','w')
    p = Popen(
        ["lvalert_send",
         "--username=gracedb",
         "--password=w4k3upal1ve",
         "--file=-",
         "--node=cbc_mbta_online"
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

#def issueAlertX(event, location):
#    username = "gracedb"
#    server = "lvalert.phys.uwm.edu"
#    resource = "sender"
#    password = "w4k3upal1ve"
#    node = "cbc_mbta_online"
#    voevent = createPayload(event.graceid(), location)
#
#    myjid=JID(username+"@"+server+"/"+resource)
#    recpt=JID("pubsub."+server)
#
#    s=MyClient(jid=myjid, password=password, recpt=recpt)
#    s.connect()
#    s.send_myevent(voevent, node)
#    s.loop(1)
#
#def createPayload (uid, filename):
#    template = """<?xml version='1.0' encoding='utf-8'?>
#<!DOCTYPE LIGO_LW SYSTEM "http://ldas-sw.ligo.caltech.edu/doc/ligolwAPI/html/ligolw_dtd.txt">
#<LIGO_LW>
#        <Table Name="LVAlert:table">
#                <Column Type="lstring" Name="LVAlert:uid"/>
#                <Column Type="lstring" Name="LVAlert:file"/>
#                <Stream Name="LVAlert:table" Type="Local" Delimiter=",">
#                        "%(uid)s","%(filename)s"
#                </Stream>
#        </Table>
#</LIGO_LW>
#"""
#    return template % { 'uid': uid, 'filename': filename }
#
## pubsub import must come first because it overloads part of the
## StanzaProcessor class
#from glue.lvalert import pubsub
#
#from pyxmpp.all import JID, TLSSettings
#from pyxmpp.jabber.all import Client
#
#
#class MyClient(Client):
#    def __init__(self, jid, password, recpt):
#        # if bare JID is provided add a resource -- it is required
#        if not jid.resource:
#            jid=JID(jid.node, jid.domain, "sender")
#        self.myrecpt = recpt
#
#        # we require a TLS connection
#        t=TLSSettings(require=True,verify_peer=False)
#
#        # setup client with provided connection information
#        # and identity data
#        Client.__init__(self, jid, password, \
#            auth_methods=["sasl:GSSAPI","sasl:PLAIN"], tls_settings=t)
#
#    def stream_state_changed(self,state,arg):
#        """This one is called when the state of stream connecting the component
#        to a server changes. This will usually be used to let the user
#        know what is going on."""
#        pass
#
#    def session_started(self):
#        self.stream.set_response_handlers(self.pspl, \
#            self.pspl.generic_result,self.pspl.create_error,\
#            self.pspl.create_timeout)
#        self.stream.send(self.pspl)
#
#    def idle(self):
#        if self.stream and self.session_established:
#            self.disconnect()
#        time.sleep(2)
#
#    def post_disconnect(self):
#        raise Disconnected
#
#    def send_myevent(self, voevent, node):
#        self.pspl=pubsub.PubSub(from_jid = self.jid, to_jid = self.myrecpt, stream = self, stanza_type="get")
#        self.pspl.publish(voevent,node)


# vi: sts=4 et sw=4
