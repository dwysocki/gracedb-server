from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.permissions import expose_log_to_lvem, expose_log_to_public
from core.tests.utils import GraceDbTestBase, SignoffGroupsAndUsersSetup, \
    AccessManagersGroupAndUserSetup
from events.models import Label
from superevents.utils import create_log
from .mixins import SupereventSetup


class TestSupereventDetailView(SignoffGroupsAndUsersSetup, 
    AccessManagersGroupAndUserSetup, SupereventSetup, GraceDbTestBase):
    """
    Test who can view superevent detail pages and which
    forms are shown
    """

    def test_internal_user_view_superevent(self):
        """Basic internal user can view superevent detail page w/out forms"""
        url = reverse('superevents:view',
            args=[self.internal_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context
        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # GW status form not shown for basic internal user
        self.assertFalse(context['show_gw_status_form'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_modify_permissions'])
        # No signoff forms shown for basic internal user
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])

    def test_H1_control_room_view_superevent(self):
        """
        H1 control room can see H1 operator signoff form on superevent page
        """

        # Apply H1OPS label so we can do a full test
        h1ops = Label.objects.create(name='H1OPS')
        self.internal_superevent.labelling_set.create(label=h1ops,
            creator=self.internal_user)

        # Get URL
        url = reverse('superevents:view',
            args=[self.internal_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.H1_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context
        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # GW status form not shown for basic internal user
        self.assertFalse(context['show_gw_status_form'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_modify_permissions'])
        # Only H1 operator signoff form shown
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertTrue(context['operator_signoff_authorized'])

        # Test signoff details
        self.assertTrue(context['operator_signoff_active'])
        self.assertFalse(context['operator_signoff_exists'])
        self.assertEqual(context['operator_signoff_type'],
            self.internal_superevent.signoff_set.model.SIGNOFF_TYPE_OPERATOR)
        self.assertEqual(context['operator_signoff_instrument'],
            self.internal_superevent.signoff_set.model.INSTRUMENT_H1)


    def test_advocate_view_superevent(self):
        """EM advocate user can see advocate signoff form on superevent page"""

        # Apply H1OPS label so we can do a full test
        advreq = Label.objects.create(name='ADVREQ')
        self.internal_superevent.labelling_set.create(label=advreq,
            creator=self.internal_user)

        # Get URL
        url = reverse('superevents:view',
            args=[self.internal_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.adv_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context
        # Make sure user status is correct
        self.assertTrue(context['user_is_internal'])
        self.assertFalse(context['user_is_external'])
        # GW status form not shown for basic internal user
        self.assertFalse(context['show_gw_status_form'])
        # No 'expose/hide' form for basic internal user
        self.assertFalse(context['can_modify_permissions'])
        # Only H1 operator signoff form shown
        self.assertTrue(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])

        # Test signoff details
        self.assertTrue(context['advocate_signoff_active'])
        self.assertFalse(context['advocate_signoff_exists'])
        self.assertEqual(context['advocate_signoff_type'],
            self.internal_superevent.signoff_set.model.SIGNOFF_TYPE_ADVOCATE)
        self.assertEqual(context['advocate_signoff_instrument'], '')

    def test_lvem_user_view_hidden_superevent(self):
        """LV-EM user can't view hidden superevent"""
        url = reverse('superevents:view',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_view_exposed_superevent(self):
        """LV-EM user can view exposed superevent"""
        url = reverse('superevents:view',
            args=[self.lvem_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context
        # Make sure user status is correct
        self.assertFalse(context['user_is_internal'])
        self.assertTrue(context['user_is_external'])
        self.assertTrue(context['user'].is_authenticated)
        # GW status form not shown
        self.assertFalse(context['show_gw_status_form'])
        # No 'expose/hide' form
        self.assertFalse(context['can_modify_permissions'])
        # No signoff forms shown
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertFalse(context['advocate_signoff_authorized'])

        # Public superevent
        url = reverse('superevents:view',
            args=[self.public_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_public_user_view_hidden_superevent(self):
        """Public user can't view hidden superevents"""
        # Internal superevent
        url = reverse('superevents:view',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 404)

        # LV-EM superevent
        url = reverse('superevents:view',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 404)

    def test_public_user_view_exposed_superevent(self):
        """Public user can view exposed superevent"""
        url = reverse('superevents:view',
            args=[self.public_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)

        # Test context
        context = response.context
        # Make sure user status is correct
        self.assertFalse(context['user_is_internal'])
        self.assertTrue(context['user_is_external'])
        self.assertFalse(context['user'].is_authenticated)
        # GW status form not shown
        self.assertFalse(context['show_gw_status_form'])
        # No 'expose/hide' form
        self.assertFalse(context['can_modify_permissions'])
        # No signoff forms shown
        self.assertFalse(context['advocate_signoff_authorized'])
        self.assertFalse(context['operator_signoff_authorized'])


class TestSupereventFileListView(SupereventSetup, GraceDbTestBase):
    """Test what users see in the file list for superevents"""

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventFileListView, cls).setUpTestData()

        # Create files for internal and exposed superevents
        cls.file1 = {'filename': 'file1.txt', 'content': 'test content 1'}
        cls.file2 = {'filename': 'file2.txt', 'content': 'test content 2'}
        for i in range(4):
            log1 = create_log(cls.internal_user, 'upload file1',
                cls.internal_superevent, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log2 = create_log(cls.internal_user, 'upload file2',
                cls.internal_superevent, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))
            log3 = create_log(cls.internal_user, 'upload file1',
                cls.lvem_superevent, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log4 = create_log(cls.internal_user, 'upload file2',
                cls.lvem_superevent, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))
            log5 = create_log(cls.internal_user, 'upload file1',
                cls.public_superevent, filename=cls.file1['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file1))
            log6 = create_log(cls.internal_user, 'upload file2',
                cls.public_superevent, filename=cls.file2['filename'],
                data_file=SimpleUploadedFile.from_dict(cls.file2))

    def test_internal_user_view_superevent_files(self):
        """Basic internal user can see all files"""
        url = reverse('superevents:file-list',
            args=[self.internal_superevent.superevent_id])

        # Get response and check status code
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Loop over all logs for this superevent which have a file
        # and make sure they are included in the list. Also check file_list
        # length.  We have to account for symlinks, too
        file_logs = self.internal_superevent.log_set.exclude(filename='')
        file_list = [l.versioned_filename for l in file_logs]
        symlinks = list(set([fl.filename for fl in file_logs]))
        file_list.extend(symlinks)
        self.assertEqual(len(response.context['file_list']), len(file_list))
        for f in file_list:
            self.assertIn(f, response.context['file_list'])

    def test_lvem_user_view_files_for_hidden_superevent(self):
        """LV-EM user can't view files for hidden superevent"""
        url = reverse('superevents:file-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Try exposing a log and make sure it's still a 404
        log = self.internal_superevent.log_set.exclude(filename='').first()
        expose_log_to_lvem(log)
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_view_files_for_exposed_superevent(self):
        """LV-EM user can view exposed files for exposed superevent"""
        # LV-EM superevent
        # Expose a non-symlinked log
        log = self.lvem_superevent.log_set.get(filename=self.file1['filename'],
            file_version=1)
        expose_log_to_lvem(log)
 
        # Make request and check response
        url = reverse('superevents:file-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 1)
        self.assertIn(log.versioned_filename, response.context['file_list'])

        # Public superevent
        # Expose a non-symlinked log
        log = self.public_superevent.log_set.get(
            filename=self.file1['filename'], file_version=1)
        expose_log_to_lvem(log)
 
        # Make request and check response
        url = reverse('superevents:file-list',
            args=[self.public_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 1)
        self.assertIn(log.versioned_filename, response.context['file_list'])

    def test_lvem_user_view_symlinked_files_for_exposed_superevent(self):
        """LV-EM user can view symlinked files for exposed superevent"""
        # Expose a symlinked log
        fname = self.file1['filename']
        file_logs = self.lvem_superevent.log_set.filter(filename=fname)
        max_version = max(file_logs.values_list('file_version', flat=True))
        log = file_logs.get(file_version=max_version)
        expose_log_to_lvem(log)
 
        # Make request and check response
        url = reverse('superevents:file-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 2)
        self.assertIn(log.versioned_filename, response.context['file_list'])
        self.assertIn(log.filename, response.context['file_list'])

    def test_public_user_view_files_for_hidden_superevent(self):
        """Public user can't view files for hidden superevent"""
        # Internal superevent
        url = reverse('superevents:file-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 404)

        # LV-EM superevent
        url = reverse('superevents:file-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 404)

    def test_public_user_view_files_for_exposed_superevent(self):
        """Public user can view exposed files for exposed superevent"""
        # Expose a non-symlinked log
        log = self.public_superevent.log_set.get(
            filename=self.file1['filename'], file_version=1)
        expose_log_to_public(log)
 
        # Make request and check response
        url = reverse('superevents:file-list',
            args=[self.public_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 1)
        self.assertIn(log.versioned_filename, response.context['file_list'])

    def test_public_user_view_symlinked_files_for_exposed_superevent(self):
        """Public user can view symlinked files for exposed superevent"""
        # Expose a symlinked log
        fname = self.file1['filename']
        file_logs = self.public_superevent.log_set.filter(filename=fname)
        max_version = max(file_logs.values_list('file_version', flat=True))
        log = file_logs.get(file_version=max_version)
        expose_log_to_public(log)
 
        # Make request and check response
        url = reverse('superevents:file-list',
            args=[self.public_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['file_list']), 2)
        self.assertIn(log.versioned_filename, response.context['file_list'])
        self.assertIn(log.filename, response.context['file_list'])
