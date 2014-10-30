from django.core.management.base import BaseCommand
from gracedb.models import Event, EMBBEventLog
from gracedb.models import EMGroup
from ligoauth.models import AlternateEmail
from django.conf import settings
from django.contrib.auth.models import User
import json
import re
import smtplib
from email.mime.text import MIMEText
from email import message_from_string
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
    msg = MIMEText(message)
    # Allow the 'to' argument to contain either a list (for multiple recipients)
    # or a string (for a single recipient)
    if isinstance(to, list):
        msg['To'] = ','.join(to)
        to_list = to
    else:
        msg['To'] = to
        to_list = [to]
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

        filename = args[0]
        try:
            f_obj = open(filename, 'r')
            file_contents = f_obj.read()
            f_obj.close()
            self.transcript += 'Got email with %d characters incl headers\n' % len(file_contents)
        except Exception, e:
            self.transcript += 'Could not fetch email file\n' +  str(e)
            return sendResponse(settings.EMBB_MAIL_ADMINS, 'embb submission', self.transcript)

        # Try to convert to email object.
        email_obj = message_from_string(file_contents)

        # Find the character set
        encoding = None
        try:
            encoding = email_obj.get_content_charset()
        except:
            pass

        if not encoding:
            try:
                encoding = email_obj.get_charset()
            except:
                pass

        # Get a unicode string and fix any quotation marks.
        file_contents = get_unicode_and_fix_quotes(file_contents, encoding)

        # Turn it back into an email thingy again.
        email_obj = message_from_string(file_contents)

        # Parse the email and find out who it's from.
        from_string = email_obj['from']
        try:
            # XXX Hacky way to get the stuff between the '<' and the '>'
            from_address = from_string.split('<')[1].split('>')[0]
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
            #self.transcript += 'Error: Cannot find submitter %s\n' % submitter
            self.transcript += USER_NOT_FOUND_MESSAGE % from_address
            self.transcript += str(e)
            return sendResponse(from_address, dict['SUBJECT'], self.transcript)

        # Get the body of the message and convert to lines.
        lines = email_obj.get_payload().split('\n')

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
            
        
# look for the JSON field at the end of the mail
        extra_dict = {}
        if dict.has_key('JSON'):
            try:
                extra_dict = json.loads(dict['JSON'])
                self.transcript += 'Found %d keys in JSON\n' % len(extra_dict.keys())
            except Exception, e:
                self.transcript += 'Error: Cannot parse JSON: %s\n' % dict['JSON']
                self.transcript += str(e)
                return sendResponse(from_address, dict['SUBJECT'], self.transcript)

# look for PARAM fields of the form
# PARAM:  apple=34.2
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
            return sendResponse(from_address, dict['SUBJECT'], self.transcript)

        try:
            event = Event.getByGraceid(graceid)
            self.transcript += 'Found Graceid %s\n' % graceid
        except Exception, e:
            self.transcript += 'Error: Cannot find Graceid %s\n' % graceid
            self.transcript += str(e)
            return sendResponse(from_address, dict['SUBJECT'], self.transcript)

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
            return sendResponse(from_address, dict['SUBJECT'], self.transcript)

        eel.eel_status = getpop(extra_dict, 'eel_status', 'FO')
        eel.obs_status = getpop(extra_dict, 'obs_status', 'TE')
        eel.footprintID = getpop(extra_dict, 'footprintID', '')
        eel.waveband = getpop(extra_dict, 'waveband', 'em.opt')
        eel.ra = getpop(extra_dict, 'ra', 0.0)
        eel.dec = getpop(extra_dict, 'dec', 0.0)
        eel.raWidth = getpop(extra_dict, 'raWidth', 0.0)
        eel.decWidth = getpop(extra_dict, 'decWidth', 0.0)
        eel.gpstime = getpop(extra_dict, 'gpstime', 0)
        eel.duration = getpop(extra_dict, 'duration', 0)
        eel.extra_info_dict = json.dumps(extra_dict)
        self.transcript += 'Extra_info_dict is %s\n' % eel.extra_info_dict
    
#        eel.comment = 'hello'    #   wierdchars.sub(u'', comment)
        eel.comment = comment

        try:
            eel.save()
        except Exception as e:
            self.transcript += 'Error: Could not save EEL\n'
            self.transcript += str(e)
            return sendResponse(from_address, dict['SUBJECT'], self.transcript)

        self.transcript += 'EEL is successfully saved!'
        return sendResponse(from_address, dict['SUBJECT'], self.transcript)
