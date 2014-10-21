from django.core.management.base import BaseCommand
from gracedb.models import Event, EMBBEventLog
from gracedb.models import EMGroup
from django.contrib.auth.models import User
import json
import re
import smtplib
from email.mime.text import MIMEText
wierdchars = re.compile(u'[\U00010000-\U0010ffff]')

def sendResponse(to, subject, message):
    msg = MIMEText(message)
    msg['To'] = to
    msg['From'] = 'embb@embb-dev.ligo.caltech.edu'
    msg['Subject'] = subject
    s = smtplib.SMTP('acrux.ligo.caltech.edu')
    s.sendmail('embb@embb-dev.ligo.caltech.edu', [to], msg.as_string())
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
            return sendResponse('roy.williams@ligo.org', 'embb submission', self.transcript)

        comment = ''
        dict = {}
        p = re.compile('[A-Za-z-]+:')
        body = 0
        inkey = 0
    
        for line in lines:
            if line.strip() == '': 
                body = 1
                continue
            if inkey and line[0].isspace():
                dict[key] += line
                continue
            m = p.match(line)
            if m:
                key = line[m.start():m.end()-1]
                val = line[m.end():].strip()
                dict[key] = val
                inkey = 1
            else:
                comment += line
                inkey = 0

        self.transcript += 'Found %d keys in email\n' % len(dict.keys())
        
        if not dict.has_key('JSON'):
            self.transcript += 'Error: no JSON key'
            return sendResponse(dict['From'], dict['Subject'], self.transcript)
        
        def getpop(dict, key, default):
            if dict.has_key(key):
                return dict.pop(key)
            else:
                return default
            
        
# look for the JSON field at the end of the mail
        try:
            j = json.loads(dict['JSON'])
            self.transcript += 'Found %d keys in JSON\n' % len(j.keys())
        except Exception, e:
            self.transcript += 'Error: Cannot parse JSON: %s\n' % dict['JSON']
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        graceid = getpop(j, 'graceid', None)
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
        submitter = getpop(j, 'submitter', '')
        try:
            eel.submitter = User.objects.get(username=submitter)
            self.transcript += 'Found submitter %s\n' % submitter
        except Exception, e:
            self.transcript += 'Error: Cannot find submitter %s\n' % submitter
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        # Assign a group name
        group_name = getpop(j, 'group', None)
        try:
            group = EMGroup.objects.get(name=group_name)
            eel.group = group
            self.transcript += 'Found EMGroup %s\n' % group_name
        except Exception, e:
            self.transcript += 'Error: Cannot find EMGroup =%s=\n' % group_name
            self.transcript += str(e)
            return sendResponse(dict['From'], dict['Subject'], self.transcript)

        eel.eel_status = getpop(j, 'eel_status', 'FO')
        eel.obs_status = getpop(j, 'obs_status', 'TE')
        eel.footprintID = getpop(j, 'footprintID', '')
        eel.waveband = getpop(j, 'waveband', 'em.opt')
        eel.ra = getpop(j, 'ra', 0.0)
        eel.dec = getpop(j, 'dec', 0.0)
        eel.raWidth = getpop(j, 'raWidth', 0.0)
        eel.decWidth = getpop(j, 'decWidth', 0.0)
        eel.gpstime = getpop(j, 'gpstime', 0)
        eel.duration = getpop(j, 'duration', 0)
        eel.extra_info_dict = json.dumps(j)
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
        return sendResponse(dict['From'], dict['Subject'], self.transcript)
