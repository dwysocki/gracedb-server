from django.test import TestCase
from django.test.utils import override_settings

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from guardian.models import GroupObjectPermission, UserObjectPermission
from gracedb.models import Event, GrbEvent, CoincInspiralEvent
from gracedb.models import MultiBurstEvent, Pipeline

from django.conf import settings

import json
import os
import shutil
from urllib import urlencode
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Some utilities
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
TMP_DATA_DIR = '/tmp/test_perms_data'

def get_user(category):
    if category=='public':
        return User.objects.get(first_name='John', last_name='Public')
    elif category=='lvem':
        return User.objects.get(first_name='Claudius', last_name='Ptolemy')
    elif category=='internal':
        return User.objects.get(first_name='Albert', last_name='Einstein')
    elif category=='exec':
        return User.objects.get(first_name='Spokesy', last_name='McSpokesperson')         
    elif category=='gstlal_submitter':
        return User.objects.get(last_name='GstLal CBC')
    else:
        return None
    
def get_public_coinc_event():
    ctype = ContentType.objects.get(model='CoincInspiralEvent')
    perm  = Permission.objects.get(codename='view_coincinspiralevent')
    group = Group.objects.get(name='public_users')

    perms = GroupObjectPermission.objects.filter(permission=perm,
        group=group, content_type=ctype)
    perms = list(perms)

    if len(perms) > 1:
        print "Something is wrong. Got more than one public coinc event."
        exit(1)

    if len(perms) == 0:
        print "Something is wrong. Got no public coinc events."
        exit(1)
    
    return Event.objects.get(id=perms[0].object_pk)

def get_internal_coinc_event():
    ctype = ContentType.objects.get(model='CoincInspiralEvent')
    perm  = Permission.objects.get(codename='view_coincinspiralevent')
    executives = Group.objects.get(name='executives')
    internal   = Group.objects.get(name='Communities:LSCVirgoLIGOGroupMembers')

    # Find a GroupObjectPermission object such that the only groups allowed 
    # to view are execs and internal
    for e in CoincInspiralEvent.objects.all():
        perms = GroupObjectPermission.objects.filter(permission=perm,
            object_pk=e.id, content_type=ctype)
        groups = [p.group for p in perms]
        if set(groups)==set([internal, executives]):
            break
    return e

def get_isMemberOf(user):
    return ';'.join([g.name for g in user.groups.all()])

def extra_args(user):
    if not user:
        return {}
    return {'REMOTE_USER': user.username, 'isMemberOf': get_isMemberOf(user) }

# Given a Django test client, attempt to create a CBC, gstlal, 
# LowMass event. 
EVENT_FILE = os.path.join(settings.GRACEDB_PATHS["code"],
    'gracedb/fixtures/test_perms/cbc-lm.xml')

def request_event_creation(client, user, test=False):
    event_file = open(EVENT_FILE,'r')
    url = '/events/create/'
    group = 'Test' if test else 'CBC'
    input_dict = {
        'group'      : group,
        'pipeline'   : 'gstlal',
        'search'     : 'LowMass',
        'eventFile'  : event_file,
    }
    return client.post(url, input_dict, **extra_args(user))

# A map between test users and pipelines.
PIPELINE_USER_MAP = {
    'gstlal': ['gst',],
    'Fermi': ['gdb',],
    'Swift': ['gdb',],
}

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Test Perms Class
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

class TestPerms(TestCase): 
    # I wonder if the order of loading the fixtures will matter?
    fixtures = [
        'test_perms/auth_user.json',
        'test_perms/auth_group.json',
        'test_perms/gracedb_group.json',
        'test_perms/gracedb_pipeline.json',
        'test_perms/gracedb_search.json',
        'test_perms/gracedb_label.json',
        'test_perms/gracedb_emgroup.json',
        'test_perms/gracedb_event.json',
        'test_perms/gracedb_grbevent.json',
        'test_perms/gracedb_multiburstevent.json',
        'test_perms/gracedb_coincinspiralevent.json',
        'test_perms/gracedb_singleinspiral.json',
        'test_perms/gracedb_eventlog.json',
        'test_perms/gracedb_tag.json',
    ] 

    def setUp(self):
        # Create custom permissions
        for model in [Event, GrbEvent, CoincInspiralEvent, MultiBurstEvent]:
            content_type = ContentType.objects.get(app_label='gracedb', model=model.__name__)
            name = 'Can view %s' % model.__name__.lower()
            codename = 'view_%s' % model.__name__.lower()
            Permission.objects.create(codename=codename, name=name, content_type=content_type)

        content_type = ContentType.objects.get(app_label='gracedb', model='pipeline')
        Permission.objects.create(codename="populate_pipeline", name="Can populate pipeline",
            content_type=content_type)            
            
        # Find the content type and permissions for the parent Event class.
        Event_ctype = ContentType.objects.get(model='Event')
        Event_view = Permission.objects.get(content_type=Event_ctype, 
                    codename__startswith='view')
        Event_change = Permission.objects.get(content_type=Event_ctype, 
                    codename__startswith='change')

        # Create group object permissions
        for model in [GrbEvent, CoincInspiralEvent, MultiBurstEvent]:
            # Find the content and permissions for this subclass
            content_type = ContentType.objects.get(model=model.__name__)
            view = Permission.objects.get(content_type=content_type, 
                    codename__startswith='view')
            change = Permission.objects.get(content_type=content_type, 
                    codename__startswith='change')

            # Get groups.
            public     = Group.objects.get(name='public_users')
            internal   = Group.objects.get(name='Communities:LSCVirgoLIGOGroupMembers')
            lvem       = Group.objects.get(name='gw-astronomy:LV-EM')
            executives = Group.objects.get(name='executives')

            # Each event subclass has 3 events. How to assign permissions on them?
            # event 0: public can view, lvem can view/change, plus defaults
            # event 1: lvem can view, plus defaults
            # event 2: defaults
            # defaults: internal, exec can view and change

            events = model.objects.all()

            # Add defaults for each event
            for event in events:
                GroupObjectPermission.objects.create(permission=view, group=internal, 
                    object_pk=event.id, content_type = content_type)
                GroupObjectPermission.objects.create(permission=change, group=internal, 
                    object_pk=event.id, content_type = content_type)
                GroupObjectPermission.objects.create(permission=view, group=executives, 
                    object_pk=event.id, content_type = content_type)
                GroupObjectPermission.objects.create(permission=change, group=executives, 
                    object_pk=event.id, content_type = content_type)

            # Add additional perms for event 0
            event = events[0]
            GroupObjectPermission.objects.create(permission=view, group=lvem, 
                object_pk=event.id, content_type = content_type)
            GroupObjectPermission.objects.create(permission=change, group=lvem, 
                object_pk=event.id, content_type = content_type)
            GroupObjectPermission.objects.create(permission=view, group=public, 
                object_pk=event.id, content_type = content_type)

            # Add additional perms for event 1
            event = events[1]
            GroupObjectPermission.objects.create(permission=view, group=lvem, 
                object_pk=event.id, content_type = content_type)

            # Apply the same permissions on the underlying Event
            # XXX This is rather hacky. Is there a better way?
            for event in events:
                perms = GroupObjectPermission.objects.filter(object_pk=event.id, 
                    content_type=content_type)
                for perm in perms:
                    if perm.permission.codename.startswith('view'):
                        p = Event_view
                    else:
                        p = Event_change
                    GroupObjectPermission.objects.create(permission = p,
                        group = perm.group,
                        object_pk = perm.object_pk, 
                        content_type = Event_ctype)

        # Need to refresh the perm strings on all event objects. That way we can 
        # test the searches.
        for e in Event.objects.all():
            e.refresh_perms()

        # Create user object permissions for pipeline population
        content_type = ContentType.objects.get(app_label='gracedb',model='pipeline')
        populate = Permission.objects.get(codename='populate_pipeline')

        for p in Pipeline.objects.all():
            if p.name in PIPELINE_USER_MAP.keys():
                for username in PIPELINE_USER_MAP[p.name]:
                    user = User.objects.get(username=username)
                    UserObjectPermission.objects.create(permission=populate, user=user,
                        object_pk=p.id, content_type=content_type)        

        # Create group permission for exposing/protecting events
        content_type = ContentType.objects.get(app_label='guardian',model='GroupObjectPermission')
        add_gop = Permission.objects.get(codename='add_groupobjectpermission')
        delete_gop = Permission.objects.get(codename='delete_groupobjectpermission')
        executives.permissions.add(add_gop)
        executives.permissions.add(delete_gop) 

        # Lastly, let's create a temporary data dir. 
        if not os.path.isdir(TMP_DATA_DIR):
            os.mkdir(TMP_DATA_DIR)

    def tearDown(self):
        # Get rid of that temporary data dir.
        shutil.rmtree(TMP_DATA_DIR)

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Tests of view access
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------

    # Check that the landing page can be accessed anonymously.
    def test_index_access(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    # Check that the SPInfo page can be accessed anonymously.
    def test_spinfo_access(self):
        response = self.client.get('/SPInfo')
        self.assertEqual(response.status_code, 200)

    # Check that the SPPrivacy page can be accessed anonymously.
    def test_spprivacy_access(self):
        response = self.client.get('/SPPrivacy')
        self.assertEqual(response.status_code, 200)

    # Check that the search form can be accessed anonymously.
    # XXX Actually, we don't want this right now.
#    def test_search_form_access(self):
#        response = self.client.get('/events/search/')
#        self.assertEqual(response.status_code, 200)

    # Test viewing of events by public users
    def test_public_event_access(self):
        # Of the three CBC events, only one should be publicly viewable.
        pub_coinc_event = get_public_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            url = '/events/view/%s' % e.graceid()
            response = self.client.get(url,**extra_args(get_user('public')))
            if e.graceid()==pub_coinc_event.graceid():
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 403)

    # Test viewing of events by LV-EM users
    def test_lvem_event_access(self):
        # Of the three CBC events, two should be lvem-viewable.
        internal_coinc_event = get_internal_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            url = '/events/view/%s' % e.graceid()
            response = self.client.get(url,**extra_args(get_user('lvem')))
            if e.graceid()==internal_coinc_event.graceid():
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
   
    # Test viewing of events by LIGO users
    def test_internal_event_access(self):
        for e in CoincInspiralEvent.objects.all():
            url = '/events/view/%s' % e.graceid()
            response = self.client.get(url,**extra_args(get_user('internal')))
            self.assertEqual(response.status_code, 200)

    # Test search by public users
    def test_public_search(self):
        pub_coinc_event = get_public_coinc_event()
        query = 'Test LowMass'
        url = '/events/search/flex?%s' % urlencode({'query': query})
        response = self.client.get(url,**extra_args(get_user('public')))
        res = json.loads(response.content)
        # You should only get one event ...
        self.assertEqual(res['records'],1)
        # ... and that event should be the public one.
        self.assertEqual(res['rows'][0]['id'],pub_coinc_event.id)

    # Test search by LV-EM users
    def test_lvem_search(self):
        internal_coinc_event = get_internal_coinc_event()
        query = 'Test LowMass'
        url = '/events/search/flex?%s' % urlencode({'query': query})
        response = self.client.get(url,**extra_args(get_user('lvem')))
        res = json.loads(response.content)
        # You should get two events ...
        self.assertEqual(res['records'],2)
        # ... and the missing event should be the internal one.
        ids = [r['id'] for r in res['rows']]
        self.assertTrue(internal_coinc_event.id not in ids)

    # Test search by LIGO users
    def test_internal_search(self):
        query = 'Test LowMass'
        url = '/events/search/flex?%s' % urlencode({'query': query})
        response = self.client.get(url,**extra_args(get_user('internal')))
        res = json.loads(response.content)
        # You should get all three events.
        self.assertEqual(res['records'],3)

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Tests of event annotation
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------

    # What annotation activities need to be tested?
    # - EventLog creation
    #   /events/GXXXX/log/
    #   POST dict keys: comment, tagname  (no files through web interface)
    # - Tag creation
    #   /events/GXXXX/log/N/tag/<tagname>
    #   POST dict keys: displayName
    #   test DELETE?
    # - Labelling
    #   but no way to do this through the web interface
    # - EEL creation

    # Test annotation of events user.
    def test_public_log_creation(self):
        # Choose any event. The public coinc one will do.
        event = get_public_coinc_event()
        url = '/events/%s/log/' % event.graceid()
        input_dict = {
            'comment' : 'This is a test.',
            'tagname' : 'test_tag',
        }
        response = self.client.post(url,input_dict,**extra_args(get_user('public')))
        self.assertEqual(response.status_code, 403)

    def test_public_log_tagging(self):
        # Choose any event. The public coinc one will do.
        event = get_public_coinc_event()
        # Try to add 'test_tag' to the first log entry.
        url = '/events/%s/log/1/tag/test_tag' % event.graceid()
        input_dict = {'displayName' : None,}
        response = self.client.post(url, input_dict,**extra_args(get_user('public')))
        self.assertEqual(response.status_code, 403)

    def test_public_eel_creation(self):
        # Choose any event. The public coinc one will do.
        event = get_public_coinc_event()
        url = '/events/%s/embblog/' % event.graceid()
        # Test, em.gamma, FO, TE, instrument='Test', comment='Test'
        input_dict = {
            'group'      : 'Test',
            'waveband'   : 'em.gamma',
            'eel_status' : 'FO',
            'obs_status' : 'TE',
            'comment'    : 'Test',
            'instrument' : 'Test',
        }
        response = self.client.post(url,input_dict,**extra_args(get_user('public')))
        self.assertEqual(response.status_code, 403)

    # Test annotation of events by LV-EM users
    def test_lvem_log_creation(self):
        # Should be able to annotate the public event, but no others
        public_coinc_event = get_public_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            url = '/events/%s/log/' % e.graceid()
            input_dict = {
                'comment' : 'This is a test.',
                'tagname' : 'test_tag',
            }
            response = self.client.post(url,input_dict,**extra_args(get_user('lvem')))
            if e.id==public_coinc_event.id:
                # Not an AJAX call, so redirects to event page if successful. 
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    def test_lvem_log_tagging(self):
        public_coinc_event = get_public_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            # Try to add 'test_tag' to the first log entry.
            url = '/events/%s/log/1/tag/test_tag' % e.graceid()
            input_dict = {'displayName' : None,}
            response = self.client.post(url, input_dict,**extra_args(get_user('lvem')))
            if e.id==public_coinc_event.id:
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    def test_lvem_eel_creation(self):
        public_coinc_event = get_public_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            url = '/events/%s/embblog/' % e.graceid()
            input_dict = {
                'group'      : 'Test',
                'waveband'   : 'em.gamma',
                'eel_status' : 'FO',
                'obs_status' : 'TE',
                'comment'    : 'Test',
                'instrument' : 'Test',
            }
            response = self.client.post(url,input_dict,**extra_args(get_user('lvem')))
            if e.id==public_coinc_event.id:
                self.assertEqual(response.status_code, 302)
            else:                    
                self.assertEqual(response.status_code, 403)

    # Test annotation of events by LIGO users
    def test_internal_log_creation(self):
        for e in CoincInspiralEvent.objects.all():
            url = '/events/%s/log/' % e.graceid()
            input_dict = {
                'comment' : 'This is a test.',
                'tagname' : 'test_tag',
            }
            response = self.client.post(url,input_dict,**extra_args(get_user('internal')))
            self.assertEqual(response.status_code, 302)

    def test_internal_log_tagging(self):
        for e in CoincInspiralEvent.objects.all():
            # Try to add 'test_tag' to the first log entry.
            url = '/events/%s/log/1/tag/test_tag' % e.graceid()
            input_dict = {'displayName' : None,}
            response = self.client.post(url, input_dict,**extra_args(get_user('internal')))
            self.assertEqual(response.status_code, 302)

    def test_internal_eel_creation(self):
        for e in CoincInspiralEvent.objects.all():
            url = '/events/%s/embblog/' % e.graceid()
            input_dict = {
                'group'      : 'Test',
                'waveband'   : 'em.gamma',
                'eel_status' : 'FO',
                'obs_status' : 'TE',
                'comment'    : 'Test',
                'instrument' : 'Test',
            }
            response = self.client.post(url,input_dict,**extra_args(get_user('internal')))
            self.assertEqual(response.status_code, 302)

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Tests of event creation/replacement
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------

    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    def test_cbc_event_creation(self):
        gstlal_submitter = get_user('gstlal_submitter')
        for user in User.objects.all():
            response = request_event_creation(self.client, user)
            if user.id==gstlal_submitter.id or user.is_superuser:
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    # Anybody should be able to create a test event.
    def test_test_event_creation(self):
        for user in User.objects.all():
            response = request_event_creation(self.client, user, test=True)
            self.assertEqual(response.status_code, 302)

    # We want a test of the availability of a newly created event via search.
    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    def test_search_on_new_event(self):
        gstlal_submitter = get_user('gstlal_submitter')
        response = request_event_creation(self.client, gstlal_submitter)
        redirect_url = response['Location']
        graceid = redirect_url.split('/')[-1]
        url = '/events/search/flex?%s' % urlencode({'query': graceid})
        response = self.client.get(url,**extra_args(get_user('internal')))
        res = json.loads(response.content)
        # You should get exactly one record.
        self.assertEqual(res['records'],1)

#    # Actually, you can only replace an event that you yourself created.
#    # Thus, not sure if we really need this.
#    def test_event_replacement(self):
#        pass

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Test changes to permissions
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
   
    def test_perm_creation(self):
        for user in User.objects.all():
            # choose any event
            event = CoincInspiralEvent.objects.all()[0]
            # try POST to permission creation URL
            url = '/events/%s/perms/' % event.graceid() 
            input_dict = {'action': 'expose', 'group_name': 'gw-astronomy:LV-EM'}
            response = self.client.post(url, input_dict,**extra_args(user))
            groups = [g.name for g in user.groups.all()]
            if not 'executives' in groups and not user.is_superuser:
                self.assertEqual(response.status_code, 403)
            else:
                # 302 because it redirects you back to the event
                self.assertEqual(response.status_code, 302)
