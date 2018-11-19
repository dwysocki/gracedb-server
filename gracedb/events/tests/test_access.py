from __future__ import absolute_import
import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Permission, Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from guardian.models import UserObjectPermission, GroupObjectPermission

from core.tests.utils import GraceDbTestBase, SignoffGroupsAndUsersSetup, \
    AccessManagersGroupAndUserSetup
from events.models import (
    Event, Label, Group, Pipeline, Search, GrbEvent, Signoff, Tag, EMGroup,
)
from superevents.utils import create_log
from .mixins import EventSetup, ExposeLogMixin
from ..permission_utils import assign_default_event_perms
from ..views import update_event_perms_for_group


class TestEventDetailView(SignoffGroupsAndUsersSetup, EventSetup,
    GraceDbTestBase):
    """
    Test who can view event detail pages and which forms are shown
    """

    def test_internal_user_view_event(self):
        """Basic internal user can view event detail page w/out forms"""
        url = reverse('view', args=[self.internal_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context

        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_expose_to_lvem'])
        self.assertFalse(context['can_protect_from_lvem'])
        # No signoff forms shown for basic internal user
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])

    def test_H1_control_room_view_event(self):
        """H1 control room can see H1 operator signoff form on event page"""
        # Apply H1OPS label so we can do a full test
        h1ops = Label.objects.create(name='H1OPS')
        self.internal_event.labelling_set.create(label=h1ops,
            creator=self.internal_user)

        # Get URL
        url = reverse('view', args=[self.internal_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.H1_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context

        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_expose_to_lvem'])
        self.assertFalse(context['can_protect_from_lvem'])
        # Only H1 operator signoff form is shown
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertTrue(context['operator_signoff_authorized'])
        self.assertTrue(context['operator_signoff_active'])
        self.assertEqual(context['operator_signoff_object'], None)
        self.assertEqual(context['signoff_instrument'], 'H1')
        self.assertTrue(context['signoff_form'] is not None)

    def test_advocate_view_event(self):
        """EM advocate user can see advocate signoff form on event page"""
        # Apply ADVREQ label so we can do a full test
        advreq = Label.objects.create(name='ADVREQ')
        self.internal_event.labelling_set.create(label=advreq,
            creator=self.internal_user)

        # Get URL
        url = reverse('view', args=[self.internal_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.adv_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context

        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_expose_to_lvem'])
        self.assertFalse(context['can_protect_from_lvem'])
        # Only H1 operator signoff form is shown
        self.assertTrue(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])
        self.assertTrue(context['advocate_signoff_active'])
        self.assertEqual(context['advocate_signoff_object'], None)
        self.assertTrue(context['signoff_form'] is not None)

    def test_lvem_user_view_hidden_event(self):
        """LV-EM user can't view hidden event"""
        url = reverse('view', args=[self.internal_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_view_exposed_event(self):
        """LV-EM user can view exposed event"""
        url = reverse('view', args=[self.lvem_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context

        # Make sure user status is correct
        self.assertFalse(context['user_is_internal'])
        self.assertTrue(context['user_is_external'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_expose_to_lvem'])
        self.assertFalse(context['can_protect_from_lvem'])
        # Only H1 operator signoff form is shown
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])

    def test_public_user_view_event(self):
        """Public user can't view any events"""
        for ev in Event.objects.all():
            url = reverse('view', args=[ev.graceid])

            # Get response and check status code
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)


class TestEventFileListView(ExposeLogMixin, EventSetup, GraceDbTestBase):
    """Test what users see in the file list for an event"""

    @classmethod
    def setUpTestData(cls):
        super(TestEventFileListView, cls).setUpTestData()

        # Create files for internal and exposed events
        cls.file1 = {'filename': 'file1.txt', 'content': 'test content 1'}
        cls.file2 = {'filename': 'file2.txt', 'content': 'test content 2'}
        for i in range(4):
            log1 = create_log(cls.internal_user, 'upload file1',
                cls.internal_event, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log2 = create_log(cls.internal_user, 'upload file2',
                cls.internal_event, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))
            log3 = create_log(cls.internal_user, 'upload file1',
                cls.lvem_event, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log4 = create_log(cls.internal_user, 'upload file2',
                cls.lvem_event, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))

    def test_internal_user_view_event_files(self):
        """Basic internal user can see all files"""
        url = reverse('file_list', args=[self.internal_event.graceid])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Loop over all logs for this event which have a file and make sure
        # they are included in the list. Also check file_list length.
        # We have to account for symlinks, too
        file_logs = self.internal_event.eventlog_set.exclude(filename='')
        file_list = [l.versioned_filename for l in file_logs]
        symlinks = list(set([fl.filename for fl in file_logs]))
        file_list.extend(symlinks)
        self.assertEqual(len(response.context['file_list']), len(file_list))
        for f in file_list:
            self.assertIn(f, response.context['file_list'])

    def test_lvem_user_view_files_for_hidden_event(self):
        """LV-EM user can't view files for hidden event"""
        url = reverse('file_list', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

        # Try exposing a log and make sure it's still a 403
        log = self.internal_event.eventlog_set.exclude(filename='').first()
        self.expose_log_to_lvem(log)
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_view_files_for_exposed_event(self):
        """LV-EM user can view exposed files for exposed event"""
        # LV-EM event
        # Expose a non-symlinked log
        log = self.lvem_event.eventlog_set.get(filename=self.file1['filename'],
            file_version=1)
        self.expose_log_to_lvem(log)

        # Make request and check response
        url = reverse('file_list', args=[self.lvem_event.graceid])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 1)
        self.assertIn(log.versioned_filename, response.context['file_list'])

    def test_lvem_user_view_symlinked_files_for_exposed_event(self):
        """LV-EM user can view symlinked files for exposed event"""
        # Expose a symlinked log
        fname = self.file1['filename']
        file_logs = self.lvem_event.eventlog_set.filter(filename=fname)
        max_version = max(file_logs.values_list('file_version', flat=True))
        log = file_logs.get(file_version=max_version)
        self.expose_log_to_lvem(log)

        # Make request and check response
        url = reverse('file_list', args=[self.lvem_event.graceid])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 2)
        self.assertIn(log.versioned_filename, response.context['file_list'])
        self.assertIn(log.filename, response.context['file_list'])

    def test_public_user_view_files_for_event(self):
        """Public user can't view file list for any events"""
        for ev in Event.objects.all():
            url = reverse('file_list', args=[ev.graceid])

            # Get response and check status code
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)


class TestEventFileDownloadView(ExposeLogMixin, EventSetup, GraceDbTestBase):
    """Test event file download access"""

    @classmethod
    def setUpTestData(cls):
        super(TestEventFileDownloadView, cls).setUpTestData()

        # Create files for internal and exposed events
        cls.file1 = {'filename': 'file1.txt', 'content': 'test content 1'}
        cls.file2 = {'filename': 'file2.txt', 'content': 'test content 2'}
        for i in range(4):
            log1 = create_log(cls.internal_user, 'upload file1',
                cls.internal_event, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log2 = create_log(cls.internal_user, 'upload file2',
                cls.internal_event, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))
            log3 = create_log(cls.internal_user, 'upload file1',
                cls.lvem_event, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log4 = create_log(cls.internal_user, 'upload file2',
                cls.lvem_event, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))

    def test_internal_user_get_file_for_event(self):
        """Basic internal user can download all files for all events"""
        for e in Event.objects.all():
            file_logs = e.eventlog_set.exclude(filename='')
            file_list = [l.versioned_filename for l in file_logs]
            symlinks = list(set([fl.filename for fl in file_logs]))
            file_list.extend(symlinks)
            for f in file_list:
                url = reverse('file-download', args=[
                    self.internal_event.graceid, f])
                response = self.request_as_user(url, "GET", self.internal_user)
                self.assertEqual(response.status_code, 200)

    def test_lvem_user_get_file_for_hidden_event(self):
        """LV-EM user can't download files for hidden event"""
        file_logs = self.internal_event.eventlog_set.exclude(filename='')
        file_list = [l.versioned_filename for l in file_logs]
        symlinks = list(set([fl.filename for fl in file_logs]))
        file_list.extend(symlinks)
        for f in file_list:
            url = reverse('file-download', args=[
                self.internal_event.graceid, f])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_lvem_user_get_file_for_exposed_event(self):
        """LV-EM user can download exposed files for exposed event"""
        # Expose a non-symlinked log
        log = self.lvem_event.eventlog_set.get(filename=self.file1['filename'],
            file_version=1)
        self.expose_log_to_lvem(log)

        # Make request and check response
        url = reverse('file-download', args=[self.lvem_event.graceid,
            log.versioned_filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get_symlinked_file_for_exposed_event(self):
        """LV-EM user can download symlinked files for exposed event"""
        # Expose a symlinked log
        log = self.lvem_event.eventlog_set.get(filename=self.file1['filename'],
            file_version=3)
        self.expose_log_to_lvem(log)

        # Make request and check response
        url = reverse('file-download', args=[self.lvem_event.graceid,
            log.filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_public_user_get_file_for_event(self):
        """Public user can't download files for any events"""
        for ev in Event.objects.all():
            file_logs = ev.eventlog_set.exclude(filename='')
            file_list = [l.versioned_filename for l in file_logs]
            symlinks = list(set([fl.filename for fl in file_logs]))
            file_list.extend(symlinks)
            for f in file_list:
                url = reverse('file-download', args=[ev.graceid, f])

                # Get response and check status code
                response = self.request_as_user(url, "GET")
                self.assertEqual(response.status_code, 403)


class TestEventCreationPage(GraceDbTestBase):
    """Test access to event creation page"""

    @classmethod
    def setUpClass(cls):
        super(TestEventCreationPage, cls).setUpClass()
        cls.url = reverse('create')

        # Read data file
        event_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
            "data/cbc-lm.xml"))
        fp = open(event_file, 'r')
        data_file = fp.read()
        fp.close()

        cls.event_data = {
            'group': 'fake_group',
            'pipeline': 'fake_pipeline',
            'search': 'fake_search',
            'eventFile': data_file,
        }

    @classmethod
    def setUpTestData(cls):
        super(TestEventCreationPage, cls).setUpTestData()

        # Create group, search, pipeline
        Group.objects.create(name=cls.event_data['group'])
        Pipeline.objects.create(name=cls.event_data['pipeline'])
        Search.objects.create(name=cls.event_data['search'])

        # Create test group
        Group.objects.create(name='Test')

    def test_internal_user_get(self):
        """Internal user can get to event creation page"""
        response = self.request_as_user(self.url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can't get to event creation page"""
        response = self.request_as_user(self.url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get to event creation page"""
        response = self.request_as_user(self.url, "GET")
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_user_create_event(self):
        """Basic internal user can't create production events"""
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=self.event_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You do not have permission to submit events to this pipeline.")

    def test_basic_internal_user_create_test_event(self):
        """Basic internal user can create test events"""
        test_event_data = self.event_data.copy()
        test_event_data['group'] = 'Test'

        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=test_event_data)
        self.assertEqual(response.status_code, 200)

    def test_privileged_internal_user_create_event(self):
        """Privileged internal user can create production events"""
        # Give user ability to populate pipeline
        ctype = ContentType.objects.get_for_model(Pipeline)
        perm = Permission.objects.create(codename='populate_pipeline',
            content_type=ctype)
        pipeline = Pipeline.objects.get(name=self.event_data['pipeline'])
        UserObjectPermission.objects.create(user=self.internal_user,
            object_pk=pipeline.pk, permission=perm, content_type=ctype)
        
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=self.event_data)
        self.assertEqual(response.status_code, 200)


class TestEventNeighborsView(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestEventNeighborsView, cls).setUpTestData()

        # Create neighbors for events
        for i in range(1,4):
            ev = cls.create_event('fake_group', 'fake_pipeline')
            ev.gpstime += i
            ev.save(update_fields=['gpstime'])
            assign_default_event_perms(ev)
            ev.refresh_perms()

        # Expose one neighbor to LV-EM
        cls.exposed_neighbor = ev
        lvem_obs_group = AuthGroup.objects.get(
            name=settings.LVEM_OBSERVERS_GROUP)
        update_event_perms_for_group(cls.exposed_neighbor, lvem_obs_group,
            'expose')

    def test_internal_user_view_neighbors(self):
        """Internal user can see all neighbors for event"""
        url = reverse('neighbors', args=[self.internal_event.graceid,
            '0,5'])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)
        # Three new events and self.lvem_event are neighbors
        self.assertEqual(len(response.context['nearby']), 4)

    def test_lvem_user_view_neighbors_for_hidden_event(self):
        """LV-EM user can't see neighbors for internal-only event"""
        url = reverse('neighbors', args=[self.internal_event.graceid,
            '0,5'])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_view_neighbors_for_exposed_event(self):
        """LV-EM user can see exposed neighbors for exposed event"""
        url = reverse('neighbors', args=[self.lvem_event.graceid,
            '0,5'])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        # Three new events and self.lvem_event are neighbors
        self.assertEqual(len(response.context['nearby']), 1)
        self.assertEqual(response.context['nearby'][0][1],
            self.exposed_neighbor)

    def test_public_user_view_neighbors(self):
        """Public user can't view neighbors"""
        url = reverse('neighbors', args=[self.internal_event.graceid,
            '0,5'])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


class TestEventModifyT90(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestEventModifyT90, cls).setUpTestData()

        # Create a grb event
        ext_group = Group.objects.create(name='External')
        fermi_pipeline = Pipeline.objects.create(name='Fermi')
        grb_search = Search.objects.create(name='GRB')
        cls.grb_event = GrbEvent.objects.create(group=ext_group,
            pipeline=fermi_pipeline, search=grb_search,
            submitter=cls.internal_user)
        ctype = ContentType.objects.get_for_model(GrbEvent)
        perm = Permission.objects.create(codename='view_grbevent',
            content_type=ctype)
        assign_default_event_perms(cls.grb_event)

    @classmethod
    def setUpClass(cls):
        super(TestEventModifyT90, cls).setUpClass()
        cls.t90_data = {
            'redshift': 2,
        }

    def test_basic_internal_user_t90(self):
        """Basic internal user can't t90 GRB events"""
        url = reverse('modify_t90', args=[self.grb_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
                data=self.t90_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You aren't authorized to modify GRB attributes.")

    def test_privileged_internal_user_t90(self):
        """Privileged internal user can t90 GRB events"""
        # Create permission and give to user
        ctype = ContentType.objects.get_for_model(GrbEvent)
        perm = Permission.objects.create(codename='t90_grbevent',
            content_type=ctype)
        perm.user_set.add(self.internal_user)

        # Make request and check response
        url = reverse('modify_t90', args=[self.grb_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
                data=self.t90_data)
        # 302 response code means success since we were redirected to the
        # event page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.grb_event.graceid]))
        self.grb_event.refresh_from_db()
        self.assertEqual(self.grb_event.redshift, self.t90_data['redshift'])

    def test_lvem_user_t90(self):
        """LV-EM user can't t90 GRB events"""
        url = reverse('modify_t90', args=[self.grb_event.graceid])
        response = self.request_as_user(url, "POST", self.lvem_user,
                data=self.t90_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")

    def test_public_user_t90(self):
        """Public user can't t90 GRB events"""
        url = reverse('modify_t90', args=[self.grb_event.graceid])
        response = self.request_as_user(url, "POST", data=self.t90_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")


class TestEventModifyPermissions(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventModifyPermissions, cls).setUpClass()

        # Data for modifying permissions
        cls.perm_data = {
            'group_name': settings.LVEM_OBSERVERS_GROUP,
            'action': 'expose',
        }

    def test_basic_internal_user_modify_permissions(self):
        """Basic internal user can't modify event permissions"""
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.perm_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You aren't authorized to create permission objects.")

    def test_privileged_internal_user_modify_permissions(self):
        """Privileged internal user can modify event permissions"""
        # Create relevant permissions
        ctype = ContentType.objects.get_for_model(GroupObjectPermission)
        p_add, _ = Permission.objects.get_or_create(
            codename='add_groupobjectpermission', content_type=ctype)
        p_remove, _ = Permission.objects.get_or_create(
            codename='delete_groupobjectpermission', content_type=ctype)
        
        # Give add permission to user
        p_add.user_set.add(self.internal_user)

        # Expose event
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.perm_data)
        # Success = 302 and redirect to main event detail page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.internal_event.graceid]))

        # Try to hide event - should fail with 403
        remove_data = self.perm_data.copy()
        remove_data['action'] = 'protect'
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=remove_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You aren't authorized to delete permission objects.")

        # Give remove permission to user and try again - should succeed
        p_remove.user_set.add(self.internal_user)
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=remove_data)
        # Success = 302 and redirect to main event detail page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.internal_event.graceid]))

    def test_lvem_user_modify_permissions_for_hidden_event(self):
        """LV-EM user can't modify hidden event permissions"""
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.perm_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")

    def test_lvem_user_modify_permissions_for_exposed_event(self):
        """LV-EM user can't modify exposed event permissions"""
        url = reverse('modify_permissions', args=[self.lvem_event.graceid])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.perm_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You aren't authorized to create permission objects.")

    def test_public_user_modify_permissions(self):
        """Public user can't modify event permissions"""
        url = reverse('modify_permissions', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", data=self.perm_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")


class TestEventModifySignoff(SignoffGroupsAndUsersSetup, EventSetup,
    GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventModifySignoff, cls).setUpClass()

        cls.op_signoff_data = {
            'signoff_type': 'operator',
            'action': 'create',
            'instrument': 'H1',
            'status': Signoff.OPERATOR_STATUS_OK,
        }
        cls.adv_signoff_data = {
            'signoff_type': 'advocate',
            'action': 'create',
            'status': Signoff.OPERATOR_STATUS_OK,
        }

    def test_basic_internal_user_modify_signoff(self):
        """Basic internal user can't modify event signoffs"""
        url = reverse('modify_signoff', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.internal_user,
            self.op_signoff_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
            "Unknown instrument/control room for signoff.")

    def test_H1_control_room_modify_signoff(self):
        """H1 control room can create H1 operator signoff for event"""
        # Create and apply labels so we can do a full test
        h1ops = Label.objects.create(name='H1OPS')
        h1ok = Label.objects.create(name='H1OK')
        self.internal_event.labelling_set.create(label=h1ops,
            creator=self.internal_user)

        # Get URL
        url = reverse('modify_signoff', args=[self.internal_event.graceid])

        # Make request and get response: 302 indicates success since
        # we will be redirect to the main event detail page
        response = self.request_as_user(url, "POST", self.H1_user,
            self.op_signoff_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
            reverse('view', args=[self.internal_event.graceid]))
        self.assertTrue(self.internal_event.signoff_set.exists())
        self.assertTrue(self.internal_event.signoff_set.count(), 1)
        self.assertEqual(self.op_signoff_data['status'],
            self.internal_event.signoff_set.first().status)

    def test_lvem_user_modify_signoff(self):
        """LV-EM user can't modify event signoffs"""
        # Internal-only event
        url = reverse('modify_signoff', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", self.lvem_user,
            self.op_signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")

        # Exposed event
        url = reverse('modify_signoff', args=[self.lvem_event.graceid])
        response = self.request_as_user(url, "POST", self.lvem_user,
            self.op_signoff_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
            "Unknown instrument/control room for signoff.")

    def test_public_user_modify_signoff(self):
        """Public user can't modify event signoffs"""
        url = reverse('modify_signoff', args=[self.internal_event.graceid])
        response = self.request_as_user(url, "POST", data=self.op_signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "Forbidden")


class TestEventCreateLog(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCreateLog, cls).setUpClass()

        # Event log data
        cls.log_data = {
            'comment': 'test comment',
        }

    def test_internal_user_create_log(self):
        """Internal user can create log"""
        url = reverse('logentry', args=[self.internal_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.log_data)

        # 302 and redirection to the event detail page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.internal_event.graceid]))

        # Check that log message was created
        logs = self.internal_event.eventlog_set.all()
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().comment, self.log_data['comment'])

    def test_lvem_user_create_log_hidden_event(self):
        """LV-EM user can't create log for hidden event"""
        url = reverse('logentry', args=[self.internal_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.log_data)

        # Check response and content
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

    def test_lvem_user_create_log_exposed_event(self):
        """LV-EM user can create log for exposed event"""
        url = reverse('logentry', args=[self.lvem_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.log_data)

        # 302 and redirection to the event detail page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.lvem_event.graceid]))

        # Check that log message was created
        logs = self.lvem_event.eventlog_set.all()
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().comment, self.log_data['comment'])
        self.assertIn(Tag.objects.get(name=settings.EXTERNAL_ACCESS_TAGNAME),
            logs.first().tags.all())

    def test_public_user_create_log(self):
        """Public user can't create event logs"""
        url = reverse('logentry', args=[self.internal_event.graceid, ""])
        response = self.request_as_user(url, "POST", data=self.log_data)

        # Check response and content
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')


class TestEventLogTag(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventLogTag, cls).setUpClass()

        # Store comment for log which will be exposed
        cls.exposed_log_comment = 'exposed log'

        # Tag name
        cls.tag_name = 'test_tag'

    @classmethod
    def setUpTestData(cls):
        super(TestEventLogTag, cls).setUpTestData()

        # Create LV-EM access tag
        cls.lvem_tag, _ = Tag.objects.get_or_create(
            name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Create a few log entries
        for ev in [cls.internal_event, cls.lvem_event]:
            ev.eventlog_set.create(issuer=cls.internal_user,
                comment='test comment')
            lvem_log = ev.eventlog_set.create(issuer=cls.internal_user,
                comment=cls.exposed_log_comment)
            lvem_log.tags.add(cls.lvem_tag)

    def test_internal_user_tag_log(self):
        """Internal user can tag event logs"""
        log = self.internal_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.tag_name])
        response = self.request_as_user(url, "POST", self.internal_user)

        # 302 and redirection to the event page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.internal_event.graceid]))
        # Test tags on event log
        self.assertEqual(log.tags.count(), 1)
        self.assertIn(Tag.objects.get(name=self.tag_name), log.tags.all())

    def test_lvem_user_tag_log_hidden_event(self):
        """LV-EM user can't tag event logs for hidden events"""
        # Hidden log on hidden event
        log = self.internal_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.tag_name])
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

        # Exposed log on hidden event
        log = self.internal_event.eventlog_set.get(
            comment=self.exposed_log_comment)
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.tag_name])
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

    def test_lvem_user_tag_log_exposed_event(self):
        """LV-EM user can only tag exposed logs for exposed events"""
        # Hidden log on exposed event
        log = self.lvem_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.lvem_event.graceid,
            log.N, self.tag_name])
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

        # Exposed log on exposed event
        log = self.lvem_event.eventlog_set.get(
            comment=self.exposed_log_comment)
        url = reverse('taglogentry', args=[self.lvem_event.graceid,
            log.N, self.tag_name])
        response = self.request_as_user(url, "POST", self.lvem_user)
        # 302 and redirection to the event page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.lvem_event.graceid]))
        # Test tags on event log
        self.assertEqual(log.tags.count(), 2)
        self.assertIn(Tag.objects.get(name=self.tag_name), log.tags.all())
        self.assertIn(Tag.objects.get(name=settings.EXTERNAL_ACCESS_TAGNAME),
            log.tags.all())

    def test_public_user_tag_log(self):
        """Public user can't tag logs"""
        for ev in Event.objects.all():
            for log in ev.eventlog_set.all():
                url = reverse('taglogentry', args=[ev.graceid, log.N,
                    self.tag_name])
                response = self.request_as_user(url, "POST")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.content, 'Forbidden')


class TestEventLogUntag(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventLogUntag, cls).setUpClass()

        # Store comment for log which will be exposed
        cls.exposed_log_comment = 'exposed log'

    @classmethod
    def setUpTestData(cls):
        super(TestEventLogUntag, cls).setUpTestData()

        # Create LV-EM access tag
        cls.lvem_tag, _ = Tag.objects.get_or_create(
            name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Create test access tag
        cls.test_tag, _ = Tag.objects.get_or_create(
            name='test_tag')

        # Create a few log entries, add test tag and expose one to LV-EM
        for ev in [cls.internal_event, cls.lvem_event]:
            other_log = ev.eventlog_set.create(issuer=cls.internal_user,
                comment='test comment')
            other_log.tags.add(cls.test_tag)
            lvem_log = ev.eventlog_set.create(issuer=cls.internal_user,
                comment=cls.exposed_log_comment)
            lvem_log.tags.add(cls.lvem_tag)
            lvem_log.tags.add(cls.test_tag)

    def test_internal_user_untag_log(self):
        """Internal user can untag event logs"""
        log = self.internal_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.test_tag.name])
        response = self.request_as_user(url, "DELETE", self.internal_user)

        # Returns a 200 with a message on success
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
            "Removed tag {tag} for message {N}.".format(tag=self.test_tag.name,
            N=log.N))

    def test_lvem_user_untag_log_hidden_event(self):
        """LV-EM user can't untag event logs for hidden events"""
        # Hidden log on hidden event
        log = self.internal_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.test_tag.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

        # Exposed log on hidden event
        log = self.internal_event.eventlog_set.get(
            comment=self.exposed_log_comment)
        url = reverse('taglogentry', args=[self.internal_event.graceid,
            log.N, self.test_tag.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

    def test_lvem_user_untag_log_exposed_event(self):
        """
        LV-EM user can only remove tags on exposed logs for exposed events
        """
        # Hidden log on exposed event
        log = self.lvem_event.eventlog_set.exclude(
            comment=self.exposed_log_comment).first()
        url = reverse('taglogentry', args=[self.lvem_event.graceid,
            log.N, self.test_tag.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

        # Exposed log on exposed event
        log = self.lvem_event.eventlog_set.get(
            comment=self.exposed_log_comment)
        url = reverse('taglogentry', args=[self.lvem_event.graceid,
            log.N, self.test_tag.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        # Test response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content,
            "Removed tag {tag} for message {N}.".format(tag=self.test_tag.name,
            N=log.N))
        # Test tags on event log
        self.assertEqual(log.tags.count(), 1)
        self.assertIn(self.lvem_tag, log.tags.all())

    def test_public_user_untag_log(self):
        """Public user can't untag logs"""
        for ev in Event.objects.all():
            for log in ev.eventlog_set.all():
                url = reverse('taglogentry', args=[ev.graceid, log.N,
                    self.test_tag.name])
                response = self.request_as_user(url, "DELETE")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.content, 'Forbidden')


class TestEventCreateEMObservation(EventSetup, GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCreateEMObservation, cls).setUpClass()

        # Event log data
        # Define EMObservation data for POST-ing
        cls.emgroup_name = 'fake_emgroup'
        now = datetime.datetime.now()
        start_time_list = map(lambda i:
            (now + datetime.timedelta(seconds=i)).isoformat(), [0, 1, 2, 3])
        cls.emobservation_data = {
            'group': cls.emgroup_name,
            'ra_list': [1, 2, 3, 4],
            'ra_width_list': [0.5, 0.5, 0.5, 0.5],
            'dec_list': [5, 6, 7, 8],
            'dec_width_list': [0.8, 0.8, 0.8, 0.8],
            'start_time_list': start_time_list,
            'duration_list': [1, 1, 1, 1],
            'comment': 'test comment',
        }

    @classmethod
    def setUpTestData(cls):
        super(TestEventCreateEMObservation, cls).setUpTestData()

        # Create a temporary EMGroup
        cls.emgroup = EMGroup.objects.create(name=cls.emgroup_name)

    def test_internal_user_create_emobservation(self):
        """Internal user can create emobservation"""
        url = reverse('emobservation_entry',
            args=[self.internal_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.emobservation_data)

        # 302 and redirection to the event detail page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.internal_event.graceid]))

        # Check that emobservation was created
        emos = self.internal_event.emobservation_set.all()
        self.assertEqual(emos.count(), 1)
        self.assertEqual(emos.first().comment,
            self.emobservation_data['comment'])

    def test_lvem_user_create_emobservation_hidden_event(self):
        """LV-EM user can't create emobservation for hidden event"""
        url = reverse('emobservation_entry',
            args=[self.internal_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.emobservation_data)

        # Check response and content
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'Forbidden')

    def test_lvem_user_create_emobservation_exposed_event(self):
        """LV-EM user can create emobservation for exposed event"""
        url = reverse('emobservation_entry',
            args=[self.lvem_event.graceid, ""])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.emobservation_data)

        # 302 and redirection to the event detail page means success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('view',
            args=[self.lvem_event.graceid]))

        # Check that emobservation was created
        emos = self.lvem_event.emobservation_set.all()
        self.assertEqual(emos.count(), 1)
        self.assertEqual(emos.first().comment,
            self.emobservation_data['comment'])

    def test_public_user_create_emobservation(self):
        """Public user can't create emobservations"""
        for ev in Event.objects.all():
            for log in ev.eventlog_set.all():
                url = reverse('emobservation_entry', args=[ev.graceid, ""])
                response = self.request_as_user(url, "POST")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.content, 'Forbidden')
