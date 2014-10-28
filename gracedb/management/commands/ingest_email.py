from django.core.management.base import BaseCommand
from gracedb.models import Event, EMBBEventLog
from gracedb.models import EMGroup
from django.conf import settings
from django.contrib.auth.models import User
import json
import re
import smtplib
from email.mime.text import MIMEText
wierdchars = re.compile(u'[\U00010000-\U0010ffff]')

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

class Command(BaseCommand):
    help = "I am the email ingester!"

    def handle(self, *args, **options):
        self.transcript = 'Started email ingester\n'

        filename = args[0]
        try:
            lines = open(filename).readlines()
            self.transcript += 'Got email with %d lines incl headers\n' % len(lines)
        except Exception, e:
            self.transcript += 'Could not fetch email file\n' +  str(e)
            return sendResponse(settings.EMBB_MAIL_ADMINS, 'embb submission', self.transcript)

        comment = ''
        dict = {}
        p = re.compile('[A-Za-z-]+:')
        body = 0
        inkey = 0
    
        for line in lines:
            if line.strip() == '':    # first blank line is end of headers start of body
                body = 1
                continue
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
#            return sendResponse(dict['From'], dict['Subject'], self.transcript)
        
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
                return sendResponse(dict['From'], dict['Subject'], self.transcript)

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
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        try:
            event = Event.getByGraceid(graceid)
            self.transcript += 'Found Graceid %s\n' % graceid
        except Exception, e:
            self.transcript += 'Error: Cannot find Graceid %s\n' % graceid
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        # create a log entry
        eel = EMBBEventLog(event=event)
        eel.event = event

        # find the submitter
        submitter = getpop(extra_dict, 'submitter', '')
        try:
            eel.submitter = User.objects.get(username=submitter)
            self.transcript += 'Found submitter %s\n' % submitter
        except Exception, e:
            self.transcript += 'Error: Cannot find submitter %s\n' % submitter
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        # Assign a group name
        group_name = getpop(extra_dict, 'group', None)
        try:
            group = EMGroup.objects.get(name=group_name)
            eel.group = group
            self.transcript += 'Found EMGroup %s\n' % group_name
        except Exception, e:
            self.transcript += 'Error: Cannot find EMGroup =%s=\n' % group_name
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

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
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        self.transcript += 'EEL is successfully saved!'
        tmpfile.write(self.transcript)
        return sendResponse(dict['From'], dict['Subject'], self.transcript)
