from django.core.management.base import BaseCommand
from ...models import Event, EMBBEventLog
from ...models import EMGroup
from ...models import AlternateEmail
from django.conf import settings
from django.contrib.auth.models import User
import json
import re
import smtplib
from email.mime.text import MIMEText
from email import message_from_string
from binascii import a2b_qp, a2b_base64
wierdchars = re.compile(u'[\U00010000-\U0010ffff]')

USER_NOT_FOUND_MESSAGE = """


No GraceDB user was found matching email: %s

To proceed, the following actions are recommended:

For LVC users: Please re-send your EEL using your @LIGO.org mail 
    forwarding address or a LIGO alternate mail address (i.e., an 
    address from which you can send message to LIGO mailing lists).
    
For non-LVC users: If you have not already done so, please log in 
    to the GraceDB web interface at 

    https://gracedb.ligo.org

    This will have the effect of caching your email address, and
    then you can try re-sending your EEL message. We apologize for 
    the inconvenience. 

    Also, please use the email address with which you registered
    at gw-astronomy.org. If you need to use an alternate email 
    address, we can add it to the system manually. Just send a 
    message to uwm-help@ligo.org.


"""

def sendResponse(to, subject, message):
    print message
    msg = MIMEText(message)
    # Allow the 'to' argument to contain either a list (for multiple recipients)
    # or a string (for a single recipient)
    if isinstance(to, list):
        msg['To'] = ','.join(to)
        to_list = to
    else:
        msg['To'] = to
        to_list = [to]
    # Remove any addresses to ignore
    to_list = list(set(to_list) - set(settings.EMBB_IGNORE_ADDRESSES))
    if not len(to_list):
        return None
    from_address = settings.EMBB_MAIL_ADDRESS 
    msg['From'] = from_address
    msg['Subject'] = subject
    s = smtplib.SMTP(settings.EMBB_SMTP_SERVER)
    s.sendmail(from_address, to_list, msg.as_string())
    s.quit()
    return None

# 
# Given a string and an encoding, return a unicode string with the
# 6, 9, 66, and 99 characters replaced.
#
def get_unicode_and_fix_quotes(s, encoding):
    rv = u''
    for char in s:
        if encoding:
            uchar = unicode(char, encoding)
        else:
            uchar = unicode(char)
        if ord(uchar) > 127:
            # Fix 6 and 9
            if uchar == u'\u2018' or uchar == u'\u2019':
                uchar = u"'"

            # Fix 66 and 99
            if uchar == u'\u201c' or uchar == u'\u201d':
                uchar = u'"'
        rv += uchar
    return rv

class Command(BaseCommand):
    help = "I am the email ingester!"

    def handle(self, *args, **options):
        self.transcript = 'Started email ingester\n'
        # must provide a filename
        if len(args) < 1:
            self.transcript += 'No filename provided'
            return sendResponse(settings.EMBB_MAIL_ADMINS, 'embb submission', self.transcript)

        # The file is understood to contain the raw contents of the email.
        filename = args[0]
        try:
            f = open(filename, 'r')
            data = f.read()
            f.close()
            self.transcript += 'Got email with %d characters incl headers\n' % len(data)
        except Exception, e:
            self.transcript += 'Could not fetch email file\n' +  str(e)
            return sendResponse(settings.EMBB_MAIL_ADMINS, 'embb submission', self.transcript)

        # Try to convert to email object.
        email_obj = message_from_string(data)

        # Parse the email and find out who it's from.
        from_string = email_obj['from']
        try:
            # XXX Hacky way to get the stuff between the '<' and the '>'
            from_address = from_string.split('<')[1].split('>')[0]
        except:
            try:
                from_address = email_obj._unixfrom.split()[1]
            except Exception, e:
                self.transcript += 'Problem parsing out sender address\n' + str(e)
                return sendResponse(settings.EMBB_MAIL_ADMINS, 'embb submission failure', self.transcript)

        # find the submitter
        # Look up the sender's address.
        user = None
        try:
            user = User.objects.get(email=from_address)
        except:
            pass

        try: 
            alt_email = AlternateEmail.objects.get(email=from_address)
            user = alt_email.user
            self.transcript += 'Found submitter %s\n' % user.username
        except:
            pass

        if not user:
            self.transcript += USER_NOT_FOUND_MESSAGE % from_address
            return sendResponse(from_address, 'gracedb user not found', self.transcript)

        # Get the subject of the email. Use it in the reply
        subject = email_obj.get('Subject', '')
        reply_subject = 'Re: ' + subject
    
        # Now we want to get the contents of the email.
        # Get the payload and encoding.
        encoding = None
        if email_obj.is_multipart():
            # Let's look for a plain text part.  If not, throw an error.
            msg = None
            for part in email_obj.get_payload():
                if part.get_content_type() == 'text/plain':
                    content_transfer_encoding = part.get('Content-Transfer-Encoding', None)
                    msg = part.get_payload()
                    try:
                        encoding = part.get_content_charset()  
                    except:
                        pass
            if not msg:
                self.transcript += 'We cannot parse your email because it is not plain text.\n'
                self.transcript += 'Please send plain text emails instead of just HTML.\n'
                return sendResponse(from_address, reply_subject, self.transcript)
        else:
            # not multipart. 
            msg = email_obj.get_payload()
            content_transfer_encoding = email_obj.get('Content-Transfer-Encoding', None)
            try:
                encoding = email_obj.get_content_charset()
            except:
                pass
        if content_transfer_encoding:
            if content_transfer_encoding == 'quoted-printable':
                msg = a2b_qp(msg)
            elif content_transfer_encoding == 'base64':
                msg = a2b_base64(msg)
            else:
                self.transcript += 'Your message uses an unsupported content transfer encoding.\n'
                self.transcript += 'Please use quoted-printable or base64.\n'
                return sendResponse(from_address, reply_subject, self.transcript)

        # Get a unicode string and fix any quotation marks.
        msg = get_unicode_and_fix_quotes(msg, encoding)

        # Get the body of the message and convert to lines.
        if msg:
            lines = msg.split('\n')
        else:
            lines = []

        comment = ''
        dict = {}
        p = re.compile('[A-Za-z-]+:')
        inkey = 0
        key = ''
    
        for line in lines:
            if len(line) > 0:
                if inkey and line[0].isspace():   # initial space implies continuation
                    dict[key] += line
                    continue
            m = p.match(line)
            if m:
                key = line[m.start():m.end()-1]
                val = line[m.end():].strip()
                if dict.has_key(key):            # same key again just makes a new line in val
                    dict[key] += '\n' + val
                else:
                    dict[key] = val
                inkey = 1
            else:
                comment += line
                inkey = 0

        self.transcript += 'Found %d keys in email\n' % len(dict.keys())
        
#        if not dict.has_key('JSON'):
#            self.transcript += 'Error: no JSON key'
#            return sendResponse(from_address, dict['SUBJECT'], self.transcript)
        
        def getpop(dict, key, default):
            if dict.has_key(key):
                return dict.pop(key)
            else:
                return default

        def getTextList(dict, key1, key2, default):
            val = None
            if dict.has_key(key1): val = dict[key1]
            if dict.has_key(key2): val = dict[key2]
            if val:
                if isinstance(val, list):
                    return json.dumps(val)[1:-1]
                else:
                    return str(val)
            else:
                return default
        
# look for the JSON field at the end of the mail
        extra_dict = {}
        if dict.has_key('JSON'):
            try:
                extra_dict = json.loads(dict['JSON'])
                self.transcript += 'Found %d keys in JSON\n' % len(extra_dict.keys())
            except Exception, e:
                self.transcript += 'Error: Cannot parse JSON: %s\n' % dict['JSON']
                self.transcript += str(e)
                return sendResponse(from_address, reply_subject, self.transcript)

# look for PARAM fields of the form
# PARAM:  apple=34.2 or appleList=[2,3,4]
        if dict.has_key('PARAM'):
            lines = dict['PARAM'].split('\n')

            for line in lines:
                tok = line.split('=')
                if len(tok) == 2:
                    key = tok[0].strip()
                    val = tok[1].strip()
                    extra_dict[key] = val

# gotta get the Graceid!
        graceid = getpop(extra_dict, 'graceid', None)   # try to get the graceid from the extra_dict
        if not graceid and dict.has_key('SUBJECT'):
            tok = dict['SUBJECT'].split(':')    # look for a second colon in the SUBJECT line
            graceid = tok[0].strip()

        if not graceid:
            self.transcript += 'Cannot locate GraceID in SUBJECT, JSON, or PARAM data'
            return sendResponse(from_address, reply_subject, self.transcript)

        try:
            event = Event.getByGraceid(graceid)
            self.transcript += 'Found Graceid %s\n' % graceid
        except Exception, e:
            self.transcript += 'Error: Cannot find Graceid %s\n' % graceid
            self.transcript += str(e)
            return sendResponse(from_address, reply_subject, self.transcript)

        # create a log entry
        eel = EMBBEventLog(event=event)
        eel.event = event
        eel.submitter = user

        # Assign a group name
        group_name = getpop(extra_dict, 'group', None)
        try:
            group = EMGroup.objects.get(name=group_name)
            eel.group = group
            self.transcript += 'Found EMGroup %s\n' % group_name
        except Exception, e:
            self.transcript += 'Error: Cannot find EMGroup =%s=\n' % group_name
            self.transcript += str(e)
            return sendResponse(from_address, reply_subject, self.transcript)

        eel.eel_status  = getpop(extra_dict, 'eel_status', 'FO')
        eel.obs_status  = getpop(extra_dict, 'obs_status', 'TE')
        eel.footprintID = getpop(extra_dict, 'footprintID', '')
        eel.waveband    = getpop(extra_dict, 'waveband', 'em.opt')

        eel.raList          = getTextList(extra_dict, 'ra',       'raList',       '')
        eel.decList         = getTextList(extra_dict, 'dec',      'decList',      '')
        eel.raWidthList     = getTextList(extra_dict, 'raWidth',  'raWidthList',  '')
        eel.decWidthList    = getTextList(extra_dict, 'decWidth', 'decWidthList', '')
        eel.gpstimeList     = getTextList(extra_dict, 'gpstime',  'gpstimeList',  '')
        eel.durationList    = getTextList(extra_dict, 'duration', 'durationList', '')

        eel.validateMakeRects()

        eel.extra_info_dict = json.dumps(extra_dict)
        self.transcript += 'Extra_info_dict is %s\n' % eel.extra_info_dict
    
        eel.comment = comment

        try:
            eel.save()
        except Exception as e:
            self.transcript += 'Error: Could not save EEL\n'
            self.transcript += str(e)
            return sendResponse(from_address, reply_subject, self.transcript)

        self.transcript += 'EEL is successfully saved!'
        return sendResponse(from_address, reply_subject, self.transcript)
