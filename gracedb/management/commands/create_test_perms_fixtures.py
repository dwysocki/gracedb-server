import os
import json
from StringIO import StringIO
from datetime import datetime

from gracedb.models import GrbEvent, Tag, Event
from gracedb.models import MultiBurstEvent
from django.contrib.auth.models import Group
#from gracedb.models import CoincInspiralEvent
from gracedb.models import EventLog, Labelling, SingleInspiral

from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from django.conf import settings

#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------
# Parameters
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------

OUTPUT_DIR = os.path.join(settings.ROOT_PATH, 'gracedb/fixtures/test_perms')

DUMP_ALL_ROWS_LIST = [
    'auth.Group',
    'gracedb.Group',
    'gracedb.Pipeline',
    'gracedb.Search',
    'gracedb.Label',
    'gracedb.EMGroup',
]

# Our illustrious test users:
#    john.q.public@example.com            a public user
#    claudius.ptolemy@alexu.edu.eg        an EM astronomy MOU partner
#    albert.einstein@LIGO.org             an ordinary LIGO user
#    spokesy.mcspokesperson@LIGO.org      the LSC spokesperson
#    gracedb.maintainer@LIGO.org          the GraceDB maintainer

FAKE_USER_INFO = [
    {
        'ePPN' : 'john.q.public@example.com',
        'groups' : ['public_users',],
        'first_name' : 'John',
        'last_name' : 'Public',
        'is_active' : True,
        'is_staff'  : False,
        'is_superuser' : False,
    },
    {
        'ePPN' : 'claudius.ptolemy@alexu.edu.eg',
        'groups' : ['gw-astronomy:LV-EM',],
        'first_name' : 'Claudius',
        'last_name' : 'Ptolemy',
        'is_active' : True,
        'is_staff'  : False,
        'is_superuser' : False,
    },
    {
        'ePPN' : 'albert.einstein@ligo.org',
        'groups' : ['gw-astronomy:LV-EM', 'Communities:LSCVirgoLIGOGroupMembers',],
        'first_name' : 'Albert',
        'last_name' : 'Einstein',
        'is_active' : True,
        'is_staff'  : False,
        'is_superuser' : False,
    },
    {
        'ePPN' : 'spokesy.mcspokesperson@ligo.org',
        'groups' : ['Communities:LSCVirgoLIGOGroupMembers', 'executives',],
        'first_name' : 'Spokesy',
        'last_name' : 'McSpokesperson',
        'is_active' : True,
        'is_staff'  : False,
        'is_superuser' : False,
    },
    {
        'ePPN' : 'gracedb.maintainer@ligo.org',
        'groups' : ['Communities:LSCVirgoLIGOGroupMembers', 'gw-astronomy:LV-EM',],
        'first_name' : 'Gracedb',
        'last_name' : 'Maintainer',
        'is_active' : True,
        'is_staff'  : True,
        'is_superuser' : True,
    },
]

# Decide on which events to put in the test database. In other words, we will
# grab these real events from the database, change the permissions on them,
# and use them for testing. Note that the test database is ephemeral and is
# inaccessible to the outside world.
EVENT_PK_DICT = {
    # Choose most recent 3 GRBs, since they're all pretty much the same to me.
    'gracedb.GrbEvent'           : [e.id for e in GrbEvent.objects.all()[:3]],
    # Pick some nice representative LowMass events.
    #'gracedb.CoincInspiralEvent' : [e.id for e in CoincInspiralEvent.objects.all()[:3]],
    'gracedb.CoincInspiralEvent' : [101399, 101383, 100906],
    # Again, pick most recent burst events.
    'gracedb.MultiBurstEvent'    : [e.id for e in MultiBurstEvent.objects.all()[:3]],
}

#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------
# Utilities
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------

def get_dest(model):
        filename = model.replace('.','_').lower() + '.json'
        return os.path.join(OUTPUT_DIR, filename)

def dump_for_models(models):
    for model in models:
        with open(get_dest(model),'w') as f:
            call_command('dumpdata', model, indent=4, stdout=f) 

def dump_for_pks(pk_dict):
    for model,pk_list in pk_dict.iteritems():
        if len(pk_list)==0:
            continue
        with open(get_dest(model), 'w') as f:
            call_command('dumpdata', model, indent=4, 
                primary_keys=','.join([str(i) for i in pk_list]), stdout=f) 

# Given an input list of basic dicts, transform to the output required for a data fixture
def get_user_field_dicts(user_info):
    out_list = []
    for user_dict in user_info:
        ePPN = user_dict.pop('ePPN')
        group_names = user_dict.pop('groups')

        # XXX SADNESS. The db will not let us put in the whole ePPN because 
        # length constraints work differently for the test database. It may
        # due to the test db constructor interpreting the length limits in 
        # bytes rather than characters. 
        user_dict['username'] = ePPN[:3]
        # XXX This is usually true. But probably not being flexible enough here.
        user_dict['email'] = ePPN        

        # Transform the 'groups' field into a list of pks.
        group_pks = [g.id for g in Group.objects.filter(name__in=group_names)]
        user_dict['groups'] = group_pks
        
        user_dict['user_permissions'] = []
        user_dict['password'] = 'X'
        now = datetime.now().isoformat().split('.')[0]
        user_dict['last_login'] = now
        user_dict['date_joined'] = now

        out_list.append(user_dict)
    return out_list

class ObjectList(object):
    def __init__(self, model=None, counter=1):
        self.obj_list = []
        self.model = model
        self.counter = counter

    def write(self):
        with open(get_dest(self.model), 'w') as f:
            f.write(json.dumps(self.obj_list, indent=4, sort_keys=True, separators=(',', ': ')))

class TagList(ObjectList):
    def add_tag(self, eventlog_pks, displayName, name):
        if not name:
            return
        if name.lower() in ['null', 'none',]:
            return
        self.obj_list.append({
            'pk' : self.counter,
            'model' : self.model,
            'fields' : {
                'eventlogs' : eventlog_pks,
                'displayName' : displayName,
                # XXX Again with the same problem. Can only take first 3 chars.
                'name' : name[:3],
            }
        })
        self.counter += 1

class UserList(ObjectList):
    def append_submitters(self, event_pks):
        submitters = [event.submitter for event in Event.objects.filter(id__in=event_pks)]
        user_pk_list = [user.id for user in submitters]
        content = StringIO()
        call_command('dumpdata', self.model, 
            primary_keys=','.join([str(i) for i in user_pk_list]), 
            stdout=content) 
        content.seek(0)
        self.obj_list += json.loads(content.read())
        # XXX Transform usernames to three chars 
        tmp_list = []
        for user_dict in self.obj_list:
            user_dict['fields']['username'] = user_dict['fields']['username'][:3]
            tmp_list.append(user_dict)
        self.obj_list = tmp_list

    def append_fake_users(self, user_field_dicts):
        for user_fields in user_field_dicts:
            self.obj_list.append({
                'pk' : self.counter,
                'model' : self.model,
                'fields' : user_fields,
            })
            self.counter += 1

#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------

class Command(NoArgsCommand):
    help = "Create fixtures for testing permissions."

    def handle_noargs(self, **options):

        os.chdir(settings.ROOT_PATH)

        # Dump out the tables for which we want all rows.
        print "Dumping models for which all rows are desired..."
        dump_for_models(DUMP_ALL_ROWS_LIST)

        # Dump events with a particular set of pks. Will choose the three most recent events in 
        # each category.
        event_pk_dict = EVENT_PK_DICT
         
        print "GRB Event pks: %s" % event_pk_dict['gracedb.GrbEvent']
        print "CoincInspiral Event pks: %s" % event_pk_dict['gracedb.CoincInspiralEvent']
        print "Burst Event pks: %s" % event_pk_dict['gracedb.MultiBurstEvent']

        # The pks of the event subclasses correspond to those of the underlying events.
        # So we add one more entry to our dictionary that is the concatenation of all lists.
        event_pks = []
        for pk_list in event_pk_dict.values():
            event_pks += pk_list
        event_pk_dict['gracedb.Event'] = event_pks

        print "All event pks: %s" % event_pks

        # Dump out the events.
        dump_for_pks(event_pk_dict)

        # For each table that has 'event' as a foreign key, look up the rows corresponding 
        # to those event pks and dump them.
        event_related_pk_dict = {
            'gracedb.EventLog' : [log.id for log in EventLog.objects.filter(event_id__in=event_pks)],
            'gracedb.Labelling' : [labelling.id for labelling in Labelling.objects.filter(event_id__in=event_pks)],
            'gracedb.SingleInspiral' : [si_table.id for si_table in SingleInspiral.objects.filter(event_id__in=event_pks)],
        }
        print "Labelling pks = %s" % event_related_pk_dict['gracedb.Labelling']
        dump_for_pks(event_related_pk_dict)

        # Write out a tag fixture depending on the events we got.
        tag_list = TagList(model='gracedb.tag')
        for tag in Tag.objects.all():
            # Find overlap of our event logs with those on the tag
            full_pk_list = [el.id for el in tag.eventlogs.all()]
            sub_pk_list  = event_related_pk_dict['gracedb.EventLog']
            eventlog_pks = [p for p in full_pk_list if p in sub_pk_list]
            tag_list.add_tag(eventlog_pks, tag.name, tag.displayName)
        tag_list.write()

        # Write out a user fixture depending on the events we got.
        user_list = UserList(model='auth.user', counter=10000)
        user_list.append_submitters(event_pks)
        user_field_dicts = get_user_field_dicts(FAKE_USER_INFO)
        user_list.append_fake_users(user_field_dicts)
        user_list.write()

