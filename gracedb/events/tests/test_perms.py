from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from django.conf import settings
from django.urls import reverse

from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.shortcuts import assign_perm

from events.models import Event, GrbEvent, CoincInspiralEvent, MultiBurstEvent
from events.models import Pipeline, Search, EMGroup
from events.models import Group as SGroup
from events.permission_utils import assign_default_event_perms

import json
import os
import shutil
from urllib import urlencode
    
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Some utilities
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
TMP_DATA_DIR = '/tmp/test_perms_data'
TEST_NAMES = {
    'group': 'GWGroup',
    'testgroup': 'Test',
    'pipeline': 'GWPipeline',
    'search': 'GWSearch',
    'emgroup': 'EMGroup',
}

def extra_args(user):
    """
    Utility for passing user details to request. Needed because the web server
    does some of the authentication work with Shibboleth
    """

    if not user:
        return {}

    # Information needed from webserver
    AUTH_DICT = {
        'REMOTE_USER': user.username,
        'isMemberOf': ';'.join([g.name for g in user.groups.all()]),
    }

    # Need to handle reverse proxy case where headers are used
    # instead of Apache environment variables.
    if settings.USE_X_FORWARDED_HOST:
        for k in AUTH_DICT.keys():
            AUTH_DICT['HTTP_' + k.upper()] = AUTH_DICT.pop(k)

    return AUTH_DICT

def request_event_creation(client, user, test=False):
    """
    Given a Django test client, attempt to create a CBC, gstlal,
    LowMass event.
    """
    EVENT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
        "data/cbc-lm.xml"))

    event_file = open(EVENT_FILE, 'r')
    url = reverse('create')
    group = TEST_NAMES['testgroup'] if test else TEST_NAMES['group']
    input_dict = {
        'group': group,
        'pipeline': TEST_NAMES['pipeline'],
        'search': TEST_NAMES['search'],
        'eventFile': event_file,
    }
    response = client.post(url, input_dict, **extra_args(user))
    return response

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
    """Class for testing event view permissions"""

    @classmethod
    def setUpTestData(cls):
        """Overhead for running all permissions tests"""

        # Public group name
        PUBLIC_GROUP = 'public_users'

        # Get or create auth groups
        cls.internal_group, _ = Group.objects.get_or_create(
            name=settings.LVC_GROUP)
        cls.lvem_group, _ = Group.objects.get_or_create(
            name=settings.LVEM_GROUP)
        cls.public_group, _ = Group.objects.get_or_create(name=PUBLIC_GROUP)
        cls.execs_group, _ = Group.objects.get_or_create(
            name=settings.EXEC_GROUP)

        # Get or create users
        cls.internal_user, _ = User.objects.get_or_create(
            username='internal.user')
        cls.lvem_user, _ = User.objects.get_or_create(username='lvem.user')
        cls.public_user, _ = User.objects.get_or_create(username='public.user')
        cls.exec_user, _ = User.objects.get_or_create(username='exec.user')
        cls.pipeline_user, _ = User.objects.get_or_create(
            username='pipeline.user')

        # Add users to groups
        cls.internal_group.user_set.add(cls.internal_user)
        cls.internal_group.user_set.add(cls.pipeline_user)
        cls.lvem_group.user_set.add(cls.lvem_user)
        cls.public_group.user_set.add(cls.public_user)
        cls.execs_group.user_set.add(cls.exec_user)

        # Get or create custom view permissions
        for model in [Event, GrbEvent, CoincInspiralEvent, MultiBurstEvent]:
            content_type = ContentType.objects.get(app_label='events',
                model=model.__name__)
            name = 'Can view %s' % model.__name__.lower()
            codename = 'view_%s' % model.__name__.lower()
            p, _ = Permission.objects.get_or_create(codename=codename,
                name=name, content_type=content_type)

        # Create search group, pipeline, search. Also create a test group
        ev_group = SGroup.objects.create(name=TEST_NAMES['group'])
        test_group = SGroup.objects.create(name=TEST_NAMES['testgroup'])
        ev_pipeline = Pipeline.objects.create(name=TEST_NAMES['pipeline'])
        ev_search = Search.objects.create(name=TEST_NAMES['search'])
        
        # Create events - 1 internal, 1 lvem/internal, 1 public/lvem/internal
        # event 0: public can view, lvem can view/change, plus defaults
        # event 1: lvem can view/change, plus defaults
        # event 2: defaults
        # defaults: internal and execs can view and change
        for ev_type in ['internal_event', 'lvem_event', 'public_event']:
            ev = Event.objects.create(group=ev_group, pipeline=ev_pipeline,
                search=ev_search, gpstime=0, submitter=cls.internal_user)

            # Attach event instances to class object
            setattr(cls, ev_type, ev)

            # Add event log message
            ev.eventlog_set.create(issuer=cls.internal_user, comment="test")

            # Permissions
            assign_default_event_perms(ev)
            if (ev_type == 'public_event'):
                assign_perm('view_event', cls.lvem_group, ev)
                assign_perm('change_event', cls.lvem_group, ev)
                assign_perm('view_event', cls.public_group, ev)
            elif (ev_type == 'lvem_event'):
                assign_perm('view_event', cls.lvem_group, ev)
                assign_perm('change_event', cls.lvem_group, ev)

            # Refresh perms attached to event
            ev.refresh_perms()

        # Create an EMGroup for EEL testing
        EMGroup.objects.get_or_create(name=TEST_NAMES['emgroup'])


        # Create user object permissions for pipeline population
        content_type = ContentType.objects.get(app_label='events',
            model='pipeline')
        populate, _ = Permission.objects.get_or_create(
            codename='populate_pipeline', name="Can populate pipeline",
            content_type=content_type)
        pipeline = Pipeline.objects.get(name=TEST_NAMES['pipeline'])
        UserObjectPermission.objects.create(permission=populate,
            user=cls.pipeline_user, object_pk=pipeline.id,
            content_type=content_type)

        # Create group permission for exposing/protecting events
        content_type = ContentType.objects.get(app_label='guardian',
            model='GroupObjectPermission')
        add_gop = Permission.objects.get(codename='add_groupobjectpermission')
        delete_gop = Permission.objects.get(
            codename='delete_groupobjectpermission')
        cls.execs_group.permissions.add(add_gop)
        cls.execs_group.permissions.add(delete_gop) 

    # Need to create and destroy a temporary data directory for each test
    # since events created during tests don't persist in the database, but if
    # they were created from a file, the file still persists and causes errors
    # since the next event creation from a file uses the same id and thus, the
    # same path for its data directory.
    @classmethod
    def setUp(cls):
        # Create a temporary data dir. 
        if not os.path.isdir(TMP_DATA_DIR):
            os.mkdir(TMP_DATA_DIR)

    @classmethod
    def tearDown(cls):
        # Get rid of that temporary data dir.
        shutil.rmtree(TMP_DATA_DIR)

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    # Helper functions
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------

    def search_helper(self, query, user):
        """Helper function for search tests"""
        url = '{baseurl}?{query}'.format(baseurl=reverse('mainsearch'),
            query=urlencode({'query': query, 'results_format': 'F',
            'query_type': 'E'}))
        response = self.client.get(url, **extra_args(user))
        res = json.loads(response.content)
        return res

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    # Tests of view access
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------

    def test_index_access(self):
        """Check that the landing page can be accessed anonymously"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_spinfo_access(self):
        """Check that the SPInfo page can be accessed anonymously"""
        response = self.client.get(reverse('spinfo'))
        self.assertEqual(response.status_code, 200)

    def test_spprivacy_access(self):
        """Check that the SPPrivacy page can be accessed anonymously"""
        response = self.client.get(reverse('spprivacy'))
        self.assertEqual(response.status_code, 200)

    def test_internal_event_access(self):
        """Test viewing of events by LIGO users"""
        for e in Event.objects.all():
            url = reverse('view', args=[e.graceid()])
            response = self.client.get(url, **extra_args(self.internal_user))
            self.assertEqual(response.status_code, 200)

    def test_lvem_event_access(self):
        """Test viewing of events by LV-EM users"""

        # Only the internal event should not be viewable for LV-EM
        for e in Event.objects.all():
            url = reverse('view', args=[e.graceid()])
            response = self.client.get(url, **extra_args(self.lvem_user))
            if (e.graceid() != self.internal_event.graceid()):
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 403)

    def test_public_event_access(self):
        """Test viewing of events by public users"""

        # Only the public event should be viewable for public users
        for e in Event.objects.all():
            url = reverse('view', args=[e.graceid()])
            response = self.client.get(url, **extra_args(self.public_user))
            if (e.graceid() == self.public_event.graceid()):
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 403)

    def test_internal_search(self):
        """Test search by LIGO users"""
        query = '{group} {search}'.format(group=TEST_NAMES['group'],
            search=TEST_NAMES['search'])
        res = self.search_helper(query, self.internal_user)

        # You should get all three events.
        self.assertEqual(res['records'], 3)

    def test_lvem_search(self):
        """Test search by LV-EM users"""
        query = '{group} {search}'.format(group=TEST_NAMES['group'],
            search=TEST_NAMES['search'])
        res = self.search_helper(query, self.lvem_user)
        
        # You should get two events ...
        self.assertEqual(res['records'],2)
        # ... and the missing event should be the internal one.
        ids = [r['id'] for r in res['rows']]
        self.assertTrue(self.internal_event.id not in ids)

    def test_public_search(self):
        """Test search by public users"""
        query = '{group} {search}'.format(group=TEST_NAMES['group'],
            search=TEST_NAMES['search'])
        res = self.search_helper(query, self.public_user)

        # You should only get one event ...
        self.assertEqual(res['records'], 1)
        # ... and that event should be the public one.
        self.assertEqual(res['rows'][0]['id'], self.public_event.id)

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    # Tests of event annotation
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------

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

    def test_internal_log_creation(self):
        """Test annotation of events by LIGO users"""
        for e in Event.objects.all():
            url = reverse('logentry', args=[e.graceid(), ''])
            input_dict = {
                'comment' : 'This is a test.',
                'tagname' : 'test_tag',
            }
            response = self.client.post(url, input_dict,
                **extra_args(self.internal_user))
            # Expect 302 because user is redirected to event page
            # if successful
            self.assertEqual(response.status_code, 302)

    def test_lvem_log_creation(self):
        """Test annotation of events by LV-EM users"""
        # Should be able to annotate the LV-EM and public events
        for e in Event.objects.all():
            url = reverse('logentry', args=[e.graceid(), ''])
            input_dict = {
                'comment' : 'This is a test.',
                'tagname' : 'test_tag',
            }
            response = self.client.post(url,input_dict,
                **extra_args(self.lvem_user))

            if (e.id != self.internal_event.id):
                # Not an AJAX call, so redirects to event page if successful. 
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    def test_public_log_creation(self):
        """Test annotation of event by public user"""
        # Public user should not be able to annotate any events,
        # even publicly viewable ones
        event = self.public_event
        url = reverse('logentry', args=[event.graceid(), ''])
        input_dict = {
            'comment': 'This is a test.',
            'tagname': 'test_tag',
        }
        response = self.client.post(url, input_dict,
            **extra_args(self.public_user))
        self.assertEqual(response.status_code, 403)

    def test_internal_log_tagging(self):
        """Test event log tagging by internal user"""
        for e in Event.objects.all():
            # Try to add 'test_tag' to the first log entry.
            url = reverse('taglogentry', args=[e.graceid(), 1, 'test_tag'])
            input_dict = {'displayName': 'test_tag',}
            response = self.client.post(url, input_dict,
                **extra_args(self.internal_user))
            # Should give 302 on success due to redirect in view function
            self.assertEqual(response.status_code, 302)

    def test_lvem_log_tagging(self):
        """Test event log tagging by LV-EM user"""
        # Should be able to tag the LV-EM and public event's logs.
        for e in Event.objects.all():
            # Try to add 'test_tag' to the first log entry.
            url = reverse('taglogentry', args=[e.graceid(), 1, 'test_tag'])
            input_dict = {'displayName': 'test_tag',}
            response = self.client.post(url, input_dict,
                **extra_args(self.lvem_user))

            if (e.id != self.internal_event.id):
                # Not an AJAX call, so redirects to event page if successful.
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    def test_public_log_tagging(self):
        """Test event log tagging by public user"""
        # Public user should not be able to tag event logs, even for
        # publicly viewable events
        for e in Event.objects.all():
            # Try to add 'test_tag' to the first log entry.
            url = reverse('taglogentry', args=[e.graceid(), 1, 'test_tag'])
            input_dict = {'displayName': 'test_tag',}
            response = self.client.post(url, input_dict,
                **extra_args(self.public_user))
            self.assertEqual(response.status_code, 403)

    def test_internal_eel_creation(self):
        """Test EEL creation by internal user"""
        # Internal user should be able to create EELs for all events
        for e in Event.objects.all():
            url = reverse('embblogentry', args=[e.graceid(), ''])
            input_dict = {
                'group': TEST_NAMES['emgroup'],
                'waveband': 'em.gamma',
                'eel_status': 'FO',
                'obs_status': 'TE',
                'comment': 'Test',
                'instrument': 'Test',
            }
            response = self.client.post(url, input_dict,
                **extra_args(self.internal_user))

            # Should get a 302 since the view redirects to the
            # event page on success
            self.assertEqual(response.status_code, 302)

    def test_lvem_eel_creation(self):
        """Test EEL creation by LV-EM user"""
        # LV-EM user should be able to create EELs for LV-EM and public events
        for e in Event.objects.all():
            url = reverse('embblogentry', args=[e.graceid(), ''])
            input_dict = {
                'group': TEST_NAMES['emgroup'],
                'waveband': 'em.gamma',
                'eel_status': 'FO',
                'obs_status': 'TE',
                'comment': 'Test',
                'instrument': 'Test',
            }
            response = self.client.post(url, input_dict,
                **extra_args(self.lvem_user))
            if (e.id != self.internal_event.id):
                self.assertEqual(response.status_code, 302)
            else:                    
                self.assertEqual(response.status_code, 403)

    def test_public_eel_creation(self):
        """Test EEL creation by public user"""
        # Public user should not be able to create EELs
        event = self.public_event
        url = reverse('embblogentry', args=[event.graceid(), ''])
        # Test, em.gamma, FO, TE, instrument='Test', comment='Test'
        input_dict = {
            'group': TEST_NAMES['emgroup'],
            'waveband': 'em.gamma',
            'eel_status': 'FO',
            'obs_status': 'TE',
            'comment': 'Test',
            'instrument': 'Test',
        }
        response = self.client.post(url, input_dict,
            **extra_args(self.public_user))
        self.assertEqual(response.status_code, 403)

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    # Tests of event creation/replacement
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------

    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    def test_gw_event_creation(self):
        """Only specific users should be able to create non-Test events"""
        for user in User.objects.all():
            response = request_event_creation(self.client, user)
            if (user.id == self.pipeline_user.id or user.is_superuser):
                self.assertEqual(response.status_code, 302)
            else:
                self.assertEqual(response.status_code, 403)

    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    def test_test_event_creation(self):
        """Anybody should be able to create a Test event"""
        for user in User.objects.all():
            response = request_event_creation(self.client, user, test=True)
            self.assertEqual(response.status_code, 302)

    @override_settings(GRACEDB_DATA_DIR=TMP_DATA_DIR)
    def test_search_on_new_event(self):
        """Test the availability of a newly created event via search"""
        response = request_event_creation(self.client, self.pipeline_user)
        redirect_url = response['Location']
        graceid = redirect_url.split('/')[-1]
        res = self.search_helper(graceid, self.internal_user)
        # You should get exactly one record.
        self.assertEqual(res['records'],1)

    # Actually, you can only replace an event that you yourself created.
    # Thus, not sure if we really need this.
    # def test_event_replacement(self):
    #     pass

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    # Test changes to permissions
    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
   
    def test_perm_creation(self):
        """Test permission creation for events"""
        for user in User.objects.all():
            # choose any event
            event = self.internal_event
            # try POST to permission creation URL
            url = reverse('modify_permissions', args=[event.graceid()])
            input_dict = {
                'action': 'expose',
                'group_name': settings.LVEM_GROUP,
            }
            response = self.client.post(url, input_dict, **extra_args(user))
            if (not self.execs_group in user.groups.all()
                and not user.is_superuser):
                self.assertEqual(response.status_code, 403)
            else:
                # 302 because it redirects you back to the event
                self.assertEqual(response.status_code, 302)
            event.refresh_perms()
