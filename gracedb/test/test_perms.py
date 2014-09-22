from django.test import TestCase

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from guardian.models import GroupObjectPermission
from gracedb.models import Event, GrbEvent, CoincInspiralEvent
from gracedb.models import MultiBurstEvent
    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Some utilities
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

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

        # Create group object permissions
        for model in [GrbEvent, CoincInspiralEvent, MultiBurstEvent]:
            # Find the content type id
            content_type = ContentType.objects.get(model=model.__name__)

            # Get permission ids
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

    # Test viewing of events by public users
    def test_public_event_access(self):
        # Of the three CBC events, only one should be publicly viewable.
        # Let's figure out which one that is.
        pub_coinc_event = get_public_coinc_event()
        url = '/events/view/%s' % pub_coinc_event.graceid()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # Test annotation of events by public users

    # Test viewing of events by LV-EM users

    # Test annotation of events by LV-EM users
   
    # Test viewing of events by LIGO users

    # Test annotation of events by LIGO users

    def test_search(self):
        response = self.client.get('/events/search/')
        self.assertEqual(response.status_code, 200)

    def test_event_view(self):
        url = '/events/view/T101399'
        gracedb_maintainer = User.objects.get(first_name='Gracedb', last_name='Maintainer')
        response = self.client.get(url,REMOTE_USER=gracedb_maintainer.username)
        #print "Response content: "
        #print response.content
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Test event annotation
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Test event creation/replacement
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------

    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
    # Test changes to permissions
    #-------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------
   

