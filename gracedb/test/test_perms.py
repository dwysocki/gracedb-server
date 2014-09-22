from django.test import TestCase

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from guardian.models import GroupObjectPermission
from gracedb.models import Event, GrbEvent, CoincInspiralEvent
from gracedb.models import MultiBurstEvent

import json
from urllib import urlencode
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Some utilities
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

def get_user(category):
    if category=='public':
        return User.objects.get(first_name='John', last_name='Public')
    elif category=='lvem':
        return User.objects.get(first_name='Claudius', last_name='Ptolemy')
    elif category=='internal':
        return User.objects.get(first_name='Albert', last_name='Einstein')
    elif category=='exec':
        return User.objects.get(first_name='Spokesy', last_name='McSpokesperson')         

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

class TestPerms(TestCase): 
    # I wonder if the order of loading the fixtures will matter?
    fixtures = [
        'test_perms/auth_user.json',
        'test_perms/auth_group.json',
        'test_perms/gracedb_group.json',
        'test_perms/gracedb_label.json',
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
    def test_search_form_access(self):
        response = self.client.get('/events/search/')
        self.assertEqual(response.status_code, 200)

    # Test viewing of events by public users
    def test_public_event_access(self):
        # Of the three CBC events, only one should be publicly viewable.
        pub_coinc_event = get_public_coinc_event()
        for e in CoincInspiralEvent.objects.all():
            url = '/events/view/%s' % e.graceid()
            response = self.client.get(url,REMOTE_USER=get_user('public').username)
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
            response = self.client.get(url,REMOTE_USER=get_user('lvem').username)
            if e.graceid()==internal_coinc_event.graceid():
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
   
    # Test viewing of events by LIGO users
    def test_internal_event_access(self):
        for e in CoincInspiralEvent.objects.all():
            url = '/events/view/%s' % e.graceid()
            response = self.client.get(url,REMOTE_USER=get_user('internal').username)
            self.assertEqual(response.status_code, 200)

    # Test search by public users
    def test_public_search(self):
        pub_coinc_event = get_public_coinc_event()
        query = 'Test LowMass'
        url = '/events/search/flex?%s' % urlencode({'query': query})
        response = self.client.get(url, REMOTE_USER=get_user('public').username)
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
        response = self.client.get(url, REMOTE_USER=get_user('lvem').username)
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
        response = self.client.get(url, REMOTE_USER=get_user('internal').username)
        res = json.loads(response.content)
        # You should get all three events.
        self.assertEqual(res['records'],3)

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Tests of event annotation
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    
    # Test annotation of events by public users

    # Test annotation of events by LV-EM users

    # Test annotation of events by LIGO users

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Tests of event creation/replacement
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Test changes to permissions
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
   

