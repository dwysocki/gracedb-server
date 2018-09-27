# Test that querysets are filtered properly based on
# permissions so that users only see what they should
from __future__ import absolute_import
import datetime
import ipdb

from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from guardian.shortcuts import assign_perm, remove_perm

from api.tests.utils import GraceDbApiTestBase
from core.permission_utils import expose_log_to_lvem, expose_log_to_public
from core.tests.utils import GraceDbTestBase, \
    SupereventManagersGroupAndUserSetup, AccessManagersGroupAndUserSetup, \
    SignoffGroupsAndUsersSetup
from events.models import Label, Tag, EMGroup
from superevents.models import Superevent, Labelling, Log, VOEvent, \
    EMObservation, Signoff
from superevents.tests.mixins import SupereventCreateMixin, SupereventSetup
from superevents.utils import create_log
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


class TestSupereventListGet(SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for GET requests to the superevents list for internal,
    LV-EM, and public users.
    """

    @classmethod
    def setUpClass(cls):
        super(TestSupereventListGet, cls).setUpClass()
        cls.url = v_reverse('superevents:superevent-list')

    def test_internal_user(self):
        """Internal user sees all superevents"""
        response = self.request_as_user(self.url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Check response data - should have both superevents
        data = response.data
        superevent_ids = [s['superevent_id'] for s in data['superevents']]
        self.assertEqual(len(data['superevents']), 2)
        for s in Superevent.objects.all():
            self.assertIn(s.superevent_id, superevent_ids)

    def test_lvem_user(self):
        """LV-EM user sees only permitted superevents"""
        # Note that object permissions were already assigned
        # Get response and check code
        response = self.request_as_user(self.url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

        # Check response data - should have only lvem superevent
        data = response.data
        superevent_ids = [s['superevent_id'] for s in data['superevents']]
        self.assertEqual(len(data['superevents']), 1)
        self.assertNotIn(self.internal_superevent.superevent_id,
            superevent_ids)
        self.assertIn(self.lvem_superevent.superevent_id, superevent_ids)

    def test_public_user(self):
        """Public user sees only permitted superevents"""
        # NOTE: this will change in the near future
        pass


class TestSupereventListPost(SupereventManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for POST requests to the superevents list (i.e.,
    superevent creation) for internal, LV-EM, and public users.  Also
    tests permissions for different superevent categories (production,
    test, MDC).  Note also tha there are separate tests for "basic" internal
    users and "privileged" internal users, since "basic" internal users
    should only be able to create Test superevents.
    """

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventListPost, cls).setUpTestData()

        # Set up events for superevent creation
        p_ev = cls.create_event('testgroup', 'testpipeline',
            search_name='testsearch', user=cls.internal_user)
        t_ev = cls.create_event('Test', 'testpipeline',
            search_name='testsearch', user=cls.internal_user)
        m_ev = cls.create_event('testgroup', 'testpipeline',
            search_name='MDC', user=cls.internal_user)

        # Set up the test_data
        base_superevent_data = {
            't_start': 0,
            't_0': 1,
            't_end': 2,
        }
        cls.production_superevent_data = {
            'preferred_event': p_ev.graceid(),
            'category': Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
        }
        cls.test_superevent_data = {
            'preferred_event': t_ev.graceid(),
            'category': Superevent.SUPEREVENT_CATEGORY_TEST,
        }
        cls.mdc_superevent_data = {
            'preferred_event': m_ev.graceid(),
            'category': Superevent.SUPEREVENT_CATEGORY_MDC,
        }
        cls.production_superevent_data.update(base_superevent_data)
        cls.test_superevent_data.update(base_superevent_data)
        cls.mdc_superevent_data.update(base_superevent_data)

    @classmethod
    def setUpClass(cls):
        super(TestSupereventListPost, cls).setUpClass()
        cls.url = v_reverse('superevents:superevent-list')

    def test_basic_internal_production(self):
        """Basic internal user can't create a production superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=self.production_superevent_data)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_mdc(self):
        """Basic internal user can't create an MDC superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=self.mdc_superevent_data)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_test(self):
        """Basic internal user can create a Test superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=self.test_superevent_data)
        self.assertEqual(response.status_code, 201)

        # Quick check of data
        self.assertEqual(response.data['preferred_event'],
            self.test_superevent_data['preferred_event'])
        self.assertEqual(response.data['t_0'],
            self.test_superevent_data['t_0'])

    def test_privileged_internal_production(self):
        """Privileged internal user can create a production superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.sm_user,
            data=self.production_superevent_data)
        self.assertEqual(response.status_code, 201)

        # Quick check of data
        self.assertEqual(response.data['preferred_event'],
            self.production_superevent_data['preferred_event'])
        self.assertEqual(response.data['t_0'],
            self.production_superevent_data['t_0'])

    def test_privileged_internal_mdc(self):
        """Privileged internal user can create an MDC superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.sm_user,
            data=self.mdc_superevent_data)
        self.assertEqual(response.status_code, 201)

        # Quick check of data
        self.assertEqual(response.data['preferred_event'],
            self.mdc_superevent_data['preferred_event'])
        self.assertEqual(response.data['t_0'],
            self.mdc_superevent_data['t_0'])

    def test_privileged_internal_test(self):
        """Privileged internal user can create a test superevent"""
        # Send response
        response = self.request_as_user(self.url, "POST", self.sm_user,
            data=self.test_superevent_data)
        self.assertEqual(response.status_code, 201)

        # Quick check of data
        self.assertEqual(response.data['preferred_event'],
            self.test_superevent_data['preferred_event'])
        self.assertEqual(response.data['t_0'],
            self.test_superevent_data['t_0'])

    def test_lvem_user(self):
        """LV-EM user can't create any superevents"""
        # Production
        response = self.request_as_user(self.url, "POST", self.lvem_user,
            data=self.production_superevent_data)
        self.assertEqual(response.status_code, 403)

        # MDC
        response = self.request_as_user(self.url, "POST", self.lvem_user,
            data=self.mdc_superevent_data)
        self.assertEqual(response.status_code, 403)

        # Test
        response = self.request_as_user(self.url, "POST", self.lvem_user,
            data=self.test_superevent_data)
        self.assertEqual(response.status_code, 403)

        # Test when data is just junk
        response = self.request_as_user(self.url, "POST", self.lvem_user,
            data={"data": "NOTHING"})
        self.assertEqual(response.status_code, 403)

    def test_public_user(self):
        """Public user can't create any superevents"""
        # Production
        response = self.request_as_user(self.url, "POST",
            data=self.production_superevent_data)
        self.assertEqual(response.status_code, 403)

        # MDC
        response = self.request_as_user(self.url, "POST",
            data=self.mdc_superevent_data)
        self.assertEqual(response.status_code, 403)

        # Test
        response = self.request_as_user(self.url, "POST",
            data=self.test_superevent_data)
        self.assertEqual(response.status_code, 403)

        # Test when data is just junk
        response = self.request_as_user(self.url, "POST",
            data={"data": "NOTHING"})
        self.assertEqual(response.status_code, 403)


class TestSupereventDetail(SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for getting superevent detail pages (GET) and
    updating superevent parameters (PATCH) for internal, LV-EM, and public
    users.  We test with a variety of superevent categories since the
    required permissions are category-dependent.
    """

    def test_internal_get(self):
        """Internal user can get all superevent details"""
        for s in Superevent.objects.all():
            # Set up URL
            url = v_reverse('superevents:superevent-detail',
                args=[s.superevent_id])
            # Get response and check code
            response = self.request_as_user(url, "GET",
                self.internal_user)
            self.assertEqual(response.status_code, 200)
            # Check data on page
            self.assertEqual(response.data['superevent_id'], s.superevent_id)

    def test_lvem_get_no_view_perms(self):
        """
        LV-EM user cannot GET this superevent since object permissions
        have not been added
        """
        # Set up URL
        url = v_reverse('superevents:superevent-detail',
            args=[self.internal_superevent.superevent_id])
        # Get response and check code
        response = self.request_as_user(url, "GET", self.lvem_user)
        # Expect 404 response instead of 403, since this event is just
        # not included in the queryset due to filtering
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_with_perms(self):
        """
        LV-EM user can GET this superevent since permissions have been added
        """
        # Set up URL
        url = v_reverse('superevents:superevent-detail',
            args=[self.lvem_superevent.superevent_id])
        # Get response and check code
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        # Check data
        self.assertEqual(response.data['superevent_id'],
            self.lvem_superevent.superevent_id)

    def test_public_get_no_view_perms(self):
        """
        Public user cannot GET this URL since no permissions have been added
        """
        # TODO
        pass

    def test_public_get_with_perms(self):
        """
        Public user can GET this URL since permissions have been added
        """
        # TODO: public access
        pass

    def test_basic_internal_patch_production(self):
        """Basic internal user can't update production superevents"""
        # Define url, make request, and check response
        url = v_reverse('superevents:superevent-detail',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "PATCH", self.internal_user,
            data={'t_0': 1234})
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_patch_mdc(self):
        """Basic internal user can't update MDC superevents"""
        # Create mdc superevent
        s = self.create_superevent(self.internal_user, event_search='MDC',
            category=Superevent.SUPEREVENT_CATEGORY_MDC)
        # Define url, make request, and check response
        url = v_reverse('superevents:superevent-detail',
            args=[s.superevent_id])
        response = self.request_as_user(url, "PATCH", self.internal_user,
            data={'t_0': 1234})
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_patch_test(self):
        """Basic internal user can update test superevents"""
        # Create test superevent
        s = self.create_superevent(self.internal_user, event_group='Test',
            category=Superevent.SUPEREVENT_CATEGORY_TEST)
        # Define url, make request, and check response
        url = v_reverse('superevents:superevent-detail',
            args=[s.superevent_id])
        response = self.request_as_user(url, "PATCH", self.internal_user,
            data={'t_0': 1234})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['t_0'], 1234)


class TestSupereventConfirmAsGw(SupereventManagersGroupAndUserSetup,
    SupereventCreateMixin, GraceDbApiTestBase):
    """
    Tests permissions for POSTing to the 'superevent detail confirm-as-gw' page
    (i.e., confirming a superevent as a GW, which changes the prefix to use
    'GW' instead of 'S' and sets is_gw=True).  We test for all superevent
    categories as well, since there are category-specific permissions.  Tests
    are run for "basic" internal users, "privileged" internal users (i.e.,
    those that should be able to create non-Test superevents), LV-EM users, and
    public users.
    """

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventConfirmAsGw, cls).setUpTestData()

        # Create production superevent
        cls.production_superevent = cls.create_superevent(cls.sm_user,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)

        # Create Test superevent
        cls.test_superevent = cls.create_superevent(cls.sm_user,
            event_group='Test', category=Superevent.SUPEREVENT_CATEGORY_TEST)

        # Create MDC superevent
        cls.mdc_superevent = cls.create_superevent(cls.sm_user,
            event_search='MDC', category=Superevent.SUPEREVENT_CATEGORY_MDC)

    def test_basic_internal_user_confirm_production(self):
        """Basic internal user can't confirm production superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.production_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_user_confirm_mdc(self):
        """Basic internal user can't confirm MDC superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.mdc_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_user_confirm_test(self):
        """Basic internal user can confirm test superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.test_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user)
        self.assertEqual(response.status_code, 200)

        # Check data
        self.assertTrue('GW' in response.data['superevent_id'])

    def test_privileged_internal_user_confirm_production(self):
        """Privileged internal user can confirm production superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.production_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user)
        self.assertEqual(response.status_code, 200)

        # Check data
        self.assertTrue('GW' in response.data['superevent_id'])

    def test_privileged_internal_user_confirm_mdc(self):
        """Privileged internal user can confirm MDC superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.mdc_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user)
        self.assertEqual(response.status_code, 200)

        # Check data
        self.assertTrue('GW' in response.data['superevent_id'])

    def test_privileged_internal_user_confirm_test(self):
        """Privileged internal user can confirm test superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.test_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user)
        self.assertEqual(response.status_code, 200)

        # Check data
        self.assertTrue('GW' in response.data['superevent_id'])

    def test_lvem_user_confirm_production(self):
        """LV-EM user can't confirm production superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.production_superevent.superevent_id])

        # Make request and check response
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Expose it, should get 403 now
        assign_perm('superevents.view_superevent', self.lvem_group,
            obj=self.production_superevent)
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_confirm_mdc(self):
        """LV-EM user can't confirm mdc superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.mdc_superevent.superevent_id])

        # Make request and check response
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Expose it, should get 403 now
        assign_perm('superevents.view_superevent', self.lvem_group,
            obj=self.mdc_superevent)
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_confirm_test(self):
        """LV-EM user can't confirm test superevent as GW"""
        url = v_reverse('superevents:superevent-confirm-as-gw',
            args=[self.test_superevent.superevent_id])

        # Make request and check response
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Expose it, should get 403 now
        assign_perm('superevents.view_superevent', self.lvem_group,
            obj=self.test_superevent)
        response = self.request_as_user(url, "POST", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_confirm(self):
        """Public user can't confirm any superevents as GWs"""
        # TODO: this will have to be updated in the future
        superevents = [self.production_superevent, self.test_superevent,
            self.mdc_superevent]
        for s in superevents:
            url = v_reverse('superevents:superevent-confirm-as-gw',
                args=[s.superevent_id])
            response = self.request_as_user(url, "POST")
            self.assertEqual(response.status_code, 403)


class TestSupereventLabelList(SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for getting the list of labels attached to a
    superevent (GET) and adding a label to a superevent (POST) for
    internal, LV-EM, and public users.
    """

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLabelList, cls).setUpTestData()
        # Create labels
        l1 = Label.objects.create(name='TEST1', description='test1')
        l2 = Label.objects.create(name='TEST2', description='test1')

        # Create labelling objects
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.internal_superevent, label=l1)
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.internal_superevent, label=l2)
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.lvem_superevent, label=l1)

    def test_internal_get(self):
        """Internal user sees all labels for all superevents"""
        for s in Superevent.objects.all():
            # Set up URL
            url = v_reverse('superevents:superevent-label-list',
                args=[s.superevent_id])
            # Get response and check code
            response = self.request_as_user(url, "GET",
                self.internal_user)
            self.assertEqual(response.status_code, 200)
            # Check number of labels
            self.assertEqual(len(response.data['labels']), s.labels.count())
            # Check label content
            label_list = [l['name'] for l in response.data['labels']]
            for l in s.labels.all():
                self.assertIn(l.name, label_list)

    def test_lvem_get_no_view_perms(self):
        """LV-EM user can't see labels for internal-only superevent"""
        url = v_reverse('superevents:superevent-label-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_with_view_perms(self):
        """LV-EM user can see labels for exposed superevent"""
        url = v_reverse('superevents:superevent-label-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        # Check response data - should have all labels
        data = response.data
        self.assertEqual(len(data['labels']), 1)
        api_label_names = [l['name'] for l in data['labels']]
        for l in self.lvem_superevent.labels.all():
            self.assertIn(l.name, api_label_names)

    def test_public_get_no_view_perms(self):
        """Public user can't see labels for non-public superevents"""
        # TODO: these errors will be 404 in the future
        # Test internal superevent
        url = v_reverse('superevents:superevent-label-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 403)

        # Test LV-EM superevent
        url = v_reverse('superevents:superevent-label-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 403)

    def test_public_get_with_view_perms(self):
        """Public user can see labels for public superevents"""
        # TODO
        pass

    def test_internal_post(self):
        """Internal user can add labels to all superevents"""
        label, _ = Label.objects.get_or_create(name='NEW_LABEL')
        for s in Superevent.objects.all():
            url = v_reverse('superevents:superevent-label-list',
                args=[s.superevent_id])
            data = {'name': label.name}
            response = self.request_as_user(url, "POST", self.internal_user,
                data=data)

            # Check response code and data
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['name'], label.name)

    def test_lvem_post(self):
        """LV-EM user cannot add labels to any superevents"""
        label, _ = Label.objects.get_or_create(name='NEW_LABEL')

        # Internal-only superevent - should get 404
        url = v_reverse('superevents:superevent-label-list',
            args=[self.internal_superevent.superevent_id])
        data = {'name': label.name}
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=data)
        self.assertEqual(response.status_code, 404)

        # LV-EM superevent - should get 403
        url = v_reverse('superevents:superevent-label-list',
            args=[self.lvem_superevent.superevent_id])
        data = {'name': label.name}
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=data)
        self.assertEqual(response.status_code, 403)

    def test_public_post(self):
        """Public user cannot add labels to any superevents"""
        label, _ = Label.objects.get_or_create(name='NEW_LABEL')

        # Internal-only superevent - should get 404
        # TODO: eventually this will be a 404, 403 for now
        url = v_reverse('superevents:superevent-label-list',
            args=[self.internal_superevent.superevent_id])
        data = {'name': label.name}
        response = self.request_as_user(url, "POST", data=data)
        self.assertEqual(response.status_code, 403)

        # LV-EM superevent - should get 404
        # TODO: eventually this will be a 404, 403 for now
        url = v_reverse('superevents:superevent-label-list',
            args=[self.lvem_superevent.superevent_id])
        data = {'name': label.name}
        response = self.request_as_user(url, "POST", data=data)
        self.assertEqual(response.status_code, 403)


class TestSupereventLabelDetail(SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for getting information about a specific label attached
    to a superevent (GET) and removing a label from a superevent (DELETE) for
    internal, LV-EM, and public users.
    """

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLabelDetail, cls).setUpTestData()
        # Create labels
        l1 = Label.objects.create(name='TEST1', description='test1')
        l2 = Label.objects.create(name='TEST2', description='test1')

        # Create labelling objects
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.internal_superevent, label=l1)
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.internal_superevent, label=l2)
        Labelling.objects.create(creator=cls.internal_user, superevent=
            cls.lvem_superevent, label=l1)

    def test_internal_get(self):
        """Internal user sees all labels for all superevents"""
        for s in Superevent.objects.all():
            for l in s.labels.all():
            # Set up URL
                url = v_reverse('superevents:superevent-label-detail',
                    args=[s.superevent_id, l.name])
                # Get response and check code
                response = self.request_as_user(url, "GET",
                    self.internal_user)
                self.assertEqual(response.status_code, 200)
                # Check number of labels
                self.assertEqual(response.data['name'], l.name)

    def test_lvem_get_no_view_perms(self):
        """LV-EM user can't see labels for internal-only superevent"""
        for l in self.internal_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.internal_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "GET", self.lvem_user)
            # Should get 404 response - because of filtering, the superevent
            # should be excluded from queryset
            self.assertEqual(response.status_code, 404)

    def test_lvem_get_with_view_perms(self):
        """LV-EM user can see all labels for exposed superevent"""
        for l in self.lvem_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.lvem_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 200)
            # Check response data
            self.assertEqual(response.data['name'], l.name)

    def test_public_get_no_view_perms(self):
        """Public user can't see labels for non-public superevents"""
        # TODO: these errors will be 404 in the future
        # Test internal superevent
        for l in self.internal_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.internal_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)
        
        # Test LV-EM superevent
        for l in self.lvem_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.lvem_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)

    def test_public_get_with_view_perms(self):
        """Public user can see all labels for public superevents"""
        # TODO
        pass

    def test_internal_delete(self):
        """Internal user can remove labels from all superevents"""
        for s in Superevent.objects.all():
            for l in s.labels.all():
                url = v_reverse('superevents:superevent-label-detail',
                    args=[s.superevent_id, l.name])
                response = self.request_as_user(url, "DELETE",
                    self.internal_user)
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.data, None)
            
    def test_lvem_delete(self):
        """LV-EM user cannot remove labels from any superevents"""
        # Internal superevent - should get 404
        for l in self.internal_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.internal_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "DELETE", self.lvem_user)
            self.assertEqual(response.status_code, 404)
        # Try to delete a label that doesn't exist to ensure there is no
        # information leaked that way.
        url = v_reverse('superevents:superevent-label-detail',
            args=[self.internal_superevent.superevent_id, 'FAKE_LABEL'])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # LV-EM superevent - should get 403
        for l in self.lvem_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.lvem_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "DELETE", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_public_delete(self):
        """Public user cannot remove labels from any superevents"""
        # Internal superevent - should get 404 (TODO: 403 for now)
        for l in self.internal_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.internal_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "DELETE")
            self.assertEqual(response.status_code, 403)

        # Try to delete a label that doesn't exist to ensure there is no
        # information leaked that way. (TODO: 403 for now, will be 404)
        url = v_reverse('superevents:superevent-label-detail',
            args=[self.internal_superevent.superevent_id, 'FAKE_LABEL'])
        response = self.request_as_user(url, "DELETE")
        self.assertEqual(response.status_code, 403)

        # LV-EM superevent - should get 404 (TODO: 403 for now)
        for l in self.lvem_superevent.labels.all():
            url = v_reverse('superevents:superevent-label-detail',
                args=[self.lvem_superevent.superevent_id, l.name])
            response = self.request_as_user(url, "DELETE")
            self.assertEqual(response.status_code, 403)

        # TODO: test on a public superevent


class TestSupereventEventList(SupereventManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):
    """
    Tests permissions for viewing event list for a superevent (GET)
    and for adding an event to a superevent (POST) for internal,
    LV-EM, and public users.  Note that there are tests for different
    superevent categories since there are specific permissions for
    handling them.
    """

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventEventList, cls).setUpTestData()
        # Create events and add to superevents
        cls.event1 = cls.create_event('group1', 'pipeline1',
            search_name='search1', user=cls.internal_user)
        cls.event2 = cls.create_event('group2', 'pipeline2',
            search_name='search2', user=cls.internal_user)
        cls.internal_superevent.events.add(cls.event1)
        cls.lvem_superevent.events.add(cls.event2)

    def test_internal_get(self):
        """Internal user sees all events for superevents"""
        for s in Superevent.objects.all():
            # Set up URL
            url = v_reverse('superevents:superevent-event-list',
                args=[s.superevent_id])
            # Get response and check code
            response = self.request_as_user(url, "GET", self.internal_user)
            self.assertEqual(response.status_code, 200)
            # Check event number and graceids
            self.assertEqual(len(response.data['events']), s.events.count())
            graceid_list = [ev['graceid'] for ev in response.data['events']]
            for ev in s.events.all():
                self.assertIn(ev.graceid(), graceid_list)

    def test_lvem_get_no_view_perms(self):
        """LV-EM user can't see events for internal-only superevent"""
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_with_view_perms(self):
        """LV-EM user can see events for exposed superevent"""
        # TODO: do we deal with permissions on events too? i.e.,
        #       don't show events in the list if they aren't exposed?
        url = v_reverse('superevents:superevent-event-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        # Check response data
        data = response.data
        self.assertEqual(len(data['events']),
            self.lvem_superevent.events.count())
        graceid_list = [ev['graceid'] for ev in data['events']]
        for ev in self.lvem_superevent.events.all():
            self.assertIn(ev.graceid(), graceid_list)

    def test_public_get_no_view_perms(self):
        """Public user can't see events for non-public superevents"""
        # Internal superevent
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 403)

        # LV-EM superevent
        url = v_reverse('superevents:superevent-event-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Should get 404 response - because of filtering, this object
        # should be excluded from queryset
        self.assertEqual(response.status_code, 403)
        # TODO: will be a 404 error in the future, not 403

    def test_public_get_with_view_perms(self):
        """Public user can see events for public superevents"""
        # TODO
        pass

    def test_basic_internal_post_production(self):
        """Basic internal user can't add events to production superevents"""
        # Create production event
        ev = self.create_event('EventGroup', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_post_mdc(self):
        """Basic internal user can't add events to mdc superevents"""
        # Create MDC superevent and event
        s = self.create_superevent(self.internal_user, event_search='MDC',
            category=Superevent.SUPEREVENT_CATEGORY_MDC)
        ev = self.create_event('EventGroup', 'EventPipeline',
            search_name='MDC', user=self.internal_user)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-list',
            args=[s.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_post_test(self):
        """Basic internal user can add events to test superevents"""
        # Create test superevent and event
        s = self.create_superevent(self.internal_user, event_group='Test',
            category=Superevent.SUPEREVENT_CATEGORY_TEST)
        ev = self.create_event('Test', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code and data
        url = v_reverse('superevents:superevent-event-list',
            args=[s.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['graceid'], ev.graceid())

    def test_privileged_internal_post_production(self):
        """Privileged internal user can add events to production superevents"""
        # Create production event
        ev = self.create_event('EventGroup', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['graceid'], ev.graceid())

    def test_privileged_internal_post_mdc(self):
        """Privileged internal user can add events to mdc superevents"""
        # Create MDC superevent and event
        s = self.create_superevent(self.internal_user, event_search='MDC',
            category=Superevent.SUPEREVENT_CATEGORY_MDC)
        ev = self.create_event('EventGroup', 'EventPipeline',
            search_name='MDC', user=self.internal_user)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-list',
            args=[s.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['graceid'], ev.graceid())

    def test_privileged_internal_post_test(self):
        """Privileged internal user can add events to test superevents"""
        # Create test superevent and event
        s = self.create_superevent(self.internal_user, event_group='Test',
            category=Superevent.SUPEREVENT_CATEGORY_TEST)
        ev = self.create_event('Test', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code and data
        url = v_reverse('superevents:superevent-event-list',
            args=[s.superevent_id])
        response = self.request_as_user(url, "POST", self.sm_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['graceid'], ev.graceid())

    def test_lvem_user_post(self):
        """LV-EM user can't add events to superevents"""
        # Create an event
        ev = self.create_event('EventGroup', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code
        # Should be 404 since superevent is not exposed
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 404)

        # Expose superevent and retry, should get 403 now
        assign_perm('superevent.view_superevent', self.lvem_group,
            obj=self.internal_superevent)
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 403)

    def test_public_user_post(self):
        """Public user can't add events to superevents"""
        # Create an event
        ev = self.create_event('EventGroup', 'EventPipeline',
            user=self.internal_user)

        # Set up URL, make request, check response code
        # Should be 404 since superevent is not exposed
        url = v_reverse('superevents:superevent-event-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST",
            data={'event': ev.graceid()})
        self.assertEqual(response.status_code, 403)
        # TODO: this is 403 for now, will be 404 in the future

        # TODO: expose to public and retry, should get 403


class TestSupereventEventDetail(SupereventManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):
    # Note: event detail pages just contain the graceid and a link to the
    # event detail page in the events API.

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventEventDetail, cls).setUpTestData()
        # Create events
        cls.event1 = cls.create_event('group1', 'pipeline1',
            search_name='search1', user=cls.internal_user)
        cls.event2 = cls.create_event('group2', 'pipeline2',
            search_name='search2', user=cls.internal_user)

        # add events to superevent
        cls.internal_superevent.events.add(cls.event1)
        cls.lvem_superevent.events.add(cls.event2)

    def test_internal_get(self):
        """Internal user sees all events for superevents"""
        for s in Superevent.objects.all():
            for ev in s.events.all():
                # Set up URL
                url = v_reverse('superevents:superevent-event-detail',
                    args=[s.superevent_id, ev.graceid()])
                # Get response and check code
                response = self.request_as_user(url, "GET", self.internal_user)
                self.assertEqual(response.status_code, 200)
                # Check event number and graceids
                self.assertEqual(response.data['graceid'], ev.graceid())

    def test_lvem_get_no_view_perms(self):
        """LV-EM user can't see events for internal-only superevent"""
        for ev in self.internal_superevent.events.all():
            url = v_reverse('superevents:superevent-event-detail',
                args=[self.internal_superevent.superevent_id, ev.graceid()])
            response = self.request_as_user(url, "GET", self.lvem_user)
            # Should get 404 response - because of filtering, this superevent
            # should be excluded from the queryset
            self.assertEqual(response.status_code, 404)

    def test_lvem_get_with_view_perms(self):
        """LV-EM user can see events for exposed superevent"""
        # TODO: do we deal with permissions on events too? i.e.,
        #       don't show events in the list if they aren't exposed?
        for ev in self.lvem_superevent.events.all():
            url = v_reverse('superevents:superevent-event-detail',
                args=[self.lvem_superevent.superevent_id, ev.graceid()])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 200)
            # Check response data
            self.assertEqual(response.data['graceid'], ev.graceid())

    def test_public_get_no_view_perms(self):
        """Public user can't see events for non-public superevents"""
        # Internal superevent
        for ev in self.internal_superevent.events.all():
            url = v_reverse('superevents:superevent-event-detail',
                args=[self.internal_superevent.superevent_id, ev.graceid()])
            response = self.request_as_user(url, "GET")
            # Should get 404 response - because of filtering, this superevent
            # should be excluded from the queryset
            self.assertEqual(response.status_code, 403)
            # NOTE: will be a 404 error in the future

        for ev in self.lvem_superevent.events.all():
            url = v_reverse('superevents:superevent-event-detail',
                args=[self.lvem_superevent.superevent_id, ev.graceid()])
            response = self.request_as_user(url, "GET")
            # Should get 404 response - because of filtering, this superevent
            # should be excluded from the queryset
            self.assertEqual(response.status_code, 403)
            # NOTE: will be a 404 error in the future

    def test_public_get_with_view_perms(self):
        """Public user can see events for public superevents"""
        # TODO
        pass

    def test_basic_internal_user_remove_event_from_production_superevent(self):
        """
        Basic internal user can't remove events from production superevents.
        """
        url = v_reverse('superevents:superevent-event-detail',
            args=[self.internal_superevent.superevent_id,
            self.event1.graceid()])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_user_remove_event_from_mdc_superevent(self):
        """
        Basic internal user can't remove events from MDC superevents.
        """
        # Create MDC superevent and event, add event to superevent
        s = self.create_superevent(self.internal_user, event_search='MDC',
            category=Superevent.SUPEREVENT_CATEGORY_MDC)
        ev = self.create_event('EventGroup', 'EventPipeline',
            search_name='MDC', user=self.internal_user)
        s.events.add(ev)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-detail',
            args=[s.superevent_id, ev.graceid()])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_basic_internal_user_remove_event_from_test_superevent(self):
        """
        Basic internal user can remove events from test superevents.
        """
        # Create test superevent and event, add event to superevent
        s = self.create_superevent(self.internal_user, event_group='Test',
            category=Superevent.SUPEREVENT_CATEGORY_TEST)
        ev = self.create_event('Test', 'EventPipeline',
            user=self.internal_user)
        s.events.add(ev)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-detail',
            args=[s.superevent_id, ev.graceid()])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 204)

    def test_privileged_internal_user_remove_event_from_production_superevent(self):
        """
        Privileged internal user can remove events from production superevents.
        """
        url = v_reverse('superevents:superevent-event-detail',
            args=[self.internal_superevent.superevent_id,
            self.event1.graceid()])
        response = self.request_as_user(url, "DELETE", self.sm_user)
        self.assertEqual(response.status_code, 204)

    def test_privileged_internal_user_remove_event_from_mdc_superevent(self):
        """
        Privileged internal user can remove events from MDC superevents.
        """
        # Create MDC superevent and event, add event to superevent
        s = self.create_superevent(self.internal_user, event_search='MDC',
            category=Superevent.SUPEREVENT_CATEGORY_MDC)
        ev = self.create_event('EventGroup', 'EventPipeline',
            search_name='MDC', user=self.internal_user)
        s.events.add(ev)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-detail',
            args=[s.superevent_id, ev.graceid()])
        response = self.request_as_user(url, "DELETE", self.sm_user)
        self.assertEqual(response.status_code, 204)

    def test_privileged_internal_user_remove_event_from_test_superevent(self):
        """
        Privileged internal user can remove events from test superevents.
        """
        # Create test superevent and event, add event to superevent
        s = self.create_superevent(self.internal_user, event_group='Test',
            category=Superevent.SUPEREVENT_CATEGORY_TEST)
        ev = self.create_event('Test', 'EventPipeline',
            user=self.internal_user)
        s.events.add(ev)

        # Set up URL, make request, check response code
        url = v_reverse('superevents:superevent-event-detail',
            args=[s.superevent_id, ev.graceid()])
        response = self.request_as_user(url, "DELETE", self.sm_user)
        self.assertEqual(response.status_code, 204)

    def test_lvem_user_remove_event_from_superevent(self):
        """LV-EM user can't remove events from hidden or exposed superevents"""
        # Internal superevent
        url = v_reverse('superevents:superevent-event-detail',
            args=[self.internal_superevent.superevent_id,
            self.event1.graceid()])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Exposed superevent
        url = v_reverse('superevents:superevent-event-detail',
            args=[self.lvem_superevent.superevent_id,
            self.event2.graceid()])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_remove_event_from_superevent(self):
        """
        Public user can't remove events from hidden or exposed superevents
        """
        # Internal superevent
        url = v_reverse('superevents:superevent-event-detail',
            args=[self.internal_superevent.superevent_id,
            self.event1.graceid()])
        response = self.request_as_user(url, "DELETE")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

        # TODO: Exposed superevent


class TestSupereventLogList(AccessManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLogList, cls).setUpTestData()

        # Add logs to superevents
        cls.num_logs = 3
        for i in range(cls.num_logs):
            Log.objects.create(superevent=cls.internal_superevent,
                issuer=cls.internal_user, comment='test comment')
            Log.objects.create(superevent=cls.lvem_superevent,
                issuer=cls.internal_user, comment='test comment')

        # Expose one log on each superevent to LV-EM
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.internal_superevent.log_set.first())
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.lvem_superevent.log_set.first())
        # TODO: expose one log on each superevent to public

    def test_internal_user_get(self):
        """Internal user can see all logs for a superevent"""
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['log']),
            self.internal_superevent.log_set.count())

    def test_lvem_user_get_for_hidden_superevent(self):
        """LV-EM user can't see any logs for hidden superevent"""
        # Internal superevent even has one log exposed to LV-EM,
        # but still shouldn't be able to see it
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_for_exposed_superevent(self):
        """LV-EM user can see only exposed logs for exposed superevent"""
        url = v_reverse('superevents:superevent-log-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['log']), 1)
        self.assertEqual(response.data['log'][0]['N'],
            self.lvem_superevent.log_set.first().N)

    def test_public_user_get_for_hidden_superevent(self):
        """Public user can't see any logs for hidden superevent"""
        # TODO
        pass

    def test_internal_user_create_log(self):
        """Internal user can create logs for all superevents"""
        log_data = {'comment': 'test comment'}
        for s in Superevent.objects.all():
            url = v_reverse('superevents:superevent-log-list',
                args=[s.superevent_id])
            response = self.request_as_user(url, "POST", self.internal_user,
                data=log_data)
            # Check response and data
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['comment'], log_data['comment'])

    def test_internal_user_create_log_with_tag(self):
        """Internal user can create logs with tags for all superevents"""
        log_data = {
            'comment': 'test comment',
            'tagname': ['tag1', 'tag2']
        }
        for s in Superevent.objects.all():
            url = v_reverse('superevents:superevent-log-list',
                args=[s.superevent_id])
            response = self.request_as_user(url, "POST", self.internal_user,
                data=log_data)
            # Check response and data
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data['comment'], log_data['comment'])
            self.assertEqual(len(response.data['tag_names']),
                len(log_data['tagname']))
            for t in log_data['tagname']:
                self.assertIn(t, response.data['tag_names'])

    def test_internal_user_create_log_with_lvem_tag(self):
        """Basic internal user can't create logs with external access tag"""
        log_data = {
            'comment': 'test comment',
            'tagname': [settings.EXTERNAL_ACCESS_TAGNAME]
        }
        # Create tag
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Make request
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # Make sure correct 403 error is provided
        self.assertIn('not allowed to expose superevent log messages to LV-EM',
            response.data['detail'])

    def test_internal_user_create_log_with_public_tag(self):
        """Basic internal user can't create logs with public access tag"""
        log_data = {
            'comment': 'test comment',
            'tagname': [settings.PUBLIC_ACCESS_TAGNAME]
        }
        # Create tag
        Tag.objects.create(name=settings.PUBLIC_ACCESS_TAGNAME)

        # Make request
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # Make sure correct 403 error is provided
        self.assertIn(('not allowed to expose superevent log messages to the '
            'public'), response.data['detail'])

    def test_access_manager_create_log_with_lvem_tag(self):
        """Access manager user can create logs with external access tag"""
        log_data = {
            'comment': 'test comment',
            'tagname': [settings.EXTERNAL_ACCESS_TAGNAME]
        }
        # Create tag
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Make request
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.am_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['comment'], log_data['comment'])
        self.assertEqual(len(response.data['tag_names']), 1)
        self.assertIn(settings.EXTERNAL_ACCESS_TAGNAME,
            response.data['tag_names'])

    def test_access_manager_create_log_with_public_tag(self):
        """Access manager user can create logs with public access tag"""
        log_data = {
            'comment': 'test comment',
            'tagname': [settings.PUBLIC_ACCESS_TAGNAME]
        }
        # Create tag (have to create LV-EM too since it will be applied
        # along with the public tag)
        Tag.objects.create(name=settings.PUBLIC_ACCESS_TAGNAME)
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Make request
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.am_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['tag_names']), 2)
        self.assertIn(settings.PUBLIC_ACCESS_TAGNAME,
            response.data['tag_names'])
        self.assertIn(settings.EXTERNAL_ACCESS_TAGNAME,
            response.data['tag_names'])

    def test_lvem_user_create_log(self):
        """LV-EM user can create logs for exposed superevents only"""
        # Create tag since external users' logs will be tagged with 'lvem'
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)
        log_data = {'comment': 'test comment'}

        # Internal-only superevent
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=log_data)
        # Check response and data - 404 due to superevent not included in
        # full queryset
        self.assertEqual(response.status_code, 404)

        # LV-EM exposed superevent
        url = v_reverse('superevents:superevent-log-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['comment'], log_data['comment'])

    def test_lvem_user_create_log_with_tag(self):
        """LV-EM user can't create log with tags"""
        log_data = {'comment': 'test comment', 'tagname': ['test_tag']}

        # Post to hidden superevent, should get 404
        url = v_reverse('superevents:superevent-log-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 404)

        # Post to exposed superevent
        url = v_reverse('superevents:superevent-log-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=log_data)
        # Check response and data
        self.assertEqual(response.status_code, 403)
        self.assertIn('You are not allowed to post log messages with tags',
            response.data['detail'])

    def test_public_user_create_log(self):
        """Public user can't create any logs"""
        # TODO
        pass


class TestSupereventLogDetail(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLogDetail, cls).setUpTestData()

        # Add logs to superevents
        cls.num_logs = 3
        for i in range(cls.num_logs):
            Log.objects.create(superevent=cls.internal_superevent,
                issuer=cls.internal_user, comment='test comment')
            Log.objects.create(superevent=cls.lvem_superevent,
                issuer=cls.internal_user, comment='test comment')

        # Expose one log on each superevent to LV-EM and store them on the
        # class for easy access
        cls.internal_superevent_exposed_log = cls.internal_superevent \
            .log_set.first()
        cls.lvem_superevent_exposed_log = cls.lvem_superevent \
            .log_set.first()
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.internal_superevent_exposed_log)
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.lvem_superevent_exposed_log)

        # TODO: expose one log on each superevent to public

    def test_internal_user_get(self):
        """Internal user can see all logs for all superevents"""
        for s in Superevent.objects.all():
            for l in s.log_set.all():
                url = v_reverse('superevents:superevent-log-detail',
                    args=[self.internal_superevent.superevent_id, l.N])
                response = self.request_as_user(url, "GET",
                    self.internal_user)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['comment'], l.comment)
                self.assertEqual(response.data['N'], l.N)
            
    def test_lvem_user_get_for_hidden_superevent(self):
        """LV-EM user can't get log detail for hidden superevent"""
        # Internal superevent even has one log exposed to LV-EM,
        # but still shouldn't be able to see it
        for l in self.internal_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-detail',
                args=[self.internal_superevent.superevent_id, l.N])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_for_exposed_superevent(self):
        """LV-EM user can see only exposed logs for exposed superevent"""
        for l in self.lvem_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-detail',
                args=[self.lvem_superevent.superevent_id, l.N])
            response = self.request_as_user(url, "GET", self.lvem_user)

            if l == self.lvem_superevent_exposed_log:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['comment'],
                    self.lvem_superevent_exposed_log.comment)
                self.assertEqual(response.data['N'],
                    self.lvem_superevent_exposed_log.N)
            else:
                self.assertEqual(response.status_code, 404)

    def test_public_user_get_for_hidden_superevent(self):
        """Public user can't get log detail for hidden superevent"""
        # TODO: add public log to superevent
        for l in self.internal_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-detail',
                args=[self.internal_superevent.superevent_id, l.N])
            response = self.request_as_user(url, "GET")
            # TODO: will be 404 in the future
            self.assertEqual(response.status_code, 403)

    def test_public_user_get_for_exposed_superevent(self):
        """Public user can see only exposed logs for exposed superevent"""
        # TODO
        pass


class TestSupereventLogTagList(AccessManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLogTagList, cls).setUpTestData()

        # Add logs to superevents
        cls.num_logs = 3
        for i in range(cls.num_logs):
            Log.objects.create(superevent=cls.internal_superevent,
                issuer=cls.internal_user, comment='test comment')
            Log.objects.create(superevent=cls.lvem_superevent,
                issuer=cls.internal_user, comment='test comment')

        # Expose one log on each superevent to LV-EM and store them on the
        # class for easy access
        cls.internal_superevent_exposed_log = cls.internal_superevent \
            .log_set.first()
        cls.lvem_superevent_exposed_log = cls.lvem_superevent \
            .log_set.first()
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.internal_superevent_exposed_log)
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.lvem_superevent_exposed_log)
        # TODO: expose one log on each superevent to public

        # Create some tags
        cls.tag1 = Tag.objects.create(name='test_tag1')
        cls.tag2 = Tag.objects.create(name='test_tag2')

        # Add tags to the exposed logs
        cls.internal_superevent_exposed_log.tags.add(*(cls.tag1, cls.tag2))
        cls.lvem_superevent_exposed_log.tags.add(*(cls.tag1, cls.tag2))

    def test_internal_get(self):
        """Internal user can get all tags for all logs for all superevents"""
        for s in Superevent.objects.all():
            for l in s.log_set.all():
                url = v_reverse('superevents:superevent-log-tag-list',
                    args=[s.superevent_id, l.N])
                # Make request
                response = self.request_as_user(url, "GET", self.internal_user)
                # Check response code and data
                self.assertEqual(response.status_code, 200)
                if (l == self.internal_superevent_exposed_log or
                    l == self.lvem_superevent_exposed_log):
                    self.assertEqual(len(response.data['tags']),
                        l.tags.count())
                    response_tags = [t['name'] for t in response.data['tags']]
                    self.assertIn(self.tag1.name, response_tags)
                    self.assertIn(self.tag2.name, response_tags)
                else:
                    self.assertEqual(response.data['tags'], [])

    def test_lvem_get_for_hidden_superevent(self):
        """LV-EM user can't get tags for any logs on hidden superevent"""
        for l in self.internal_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-tag-list',
                args=[self.internal_superevent.superevent_id, l.N])
            # Make request
            response = self.request_as_user(url, "GET", self.lvem_user)
            # Check response code and data
            self.assertEqual(response.status_code, 404)

    def test_lvem_get_for_exposed_superevent(self):
        """
        LV-EM user can only get tags for exposed logs on exposed superevent
        """
        for l in self.lvem_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-tag-list',
                args=[self.lvem_superevent.superevent_id, l.N])
            # Make request
            response = self.request_as_user(url, "GET", self.lvem_user)
            # Check response code and data
            if (l == self.lvem_superevent_exposed_log):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data['tags']),
                    l.tags.count())
                response_tags = [t['name'] for t in response.data['tags']]
                self.assertIn(self.tag1.name, response_tags)
                self.assertIn(self.tag2.name, response_tags)
            else:
                self.assertEqual(response.status_code, 404)

    def test_public_get_for_hidden_superevent(self):
        """Public user can't get tags for any logs on hidden superevent"""
        for l in self.internal_superevent.log_set.all():
            url = v_reverse('superevents:superevent-log-tag-list',
                args=[self.internal_superevent.superevent_id, l.N])
            # Make request
            response = self.request_as_user(url, "GET")
            # Check response code and data
            # TODO: will be 404 in the future
            self.assertEqual(response.status_code, 403)

    def test_public_get_for_exposed_superevent(self):
        """
        Public user can only get tags for exposed logs on exposed superevent
        """
        # TODO
        pass

    def test_internal_user_tag_log(self):
        """Internal user can tag logs for all superevents"""
        tag = Tag.objects.create(name='new_tag')
        for s in Superevent.objects.all():
            for l in s.log_set.all():
                url = v_reverse('superevents:superevent-log-tag-list',
                    args=[s.superevent_id, l.N])
                response = self.request_as_user(url, "POST",
                    self.internal_user, data={'name': tag.name})
                # Check response and data
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data['name'], tag.name)

    def test_internal_user_tag_log_with_lvem(self):
        """Basic internal user can't add external access tag"""
        # Create tag
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        # Make request
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'name': settings.EXTERNAL_ACCESS_TAGNAME})
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # Make sure correct 403 error is provided
        self.assertIn('not allowed to expose superevent log messages to LV-EM',
            response.data['detail'])

    def test_internal_user_tag_log_with_public(self):
        """Basic internal user add public access tag"""
        # Create tag
        Tag.objects.create(name=settings.PUBLIC_ACCESS_TAGNAME)

        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        # Make request
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'name': settings.PUBLIC_ACCESS_TAGNAME})
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # Make sure correct 403 error is provided
        self.assertIn(('not allowed to expose superevent log messages to the '
            'public'), response.data['detail'])

    def test_access_manager_tag_log_with_lvem(self):
        """Access manager user can tag logs with external access tag"""
        # Create tag
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        # Make request
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST", self.am_user,
            data={'name': settings.EXTERNAL_ACCESS_TAGNAME})
        # Check response and data
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'],
            settings.EXTERNAL_ACCESS_TAGNAME)

    def test_access_manager_tag_log_with_public(self):
        """Access manager user can tag logs with public access tag"""
        # Create tag (have to create LV-EM too since it will be applied
        # along with the public tag)
        Tag.objects.create(name=settings.PUBLIC_ACCESS_TAGNAME)
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)

        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        # Make request
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST", self.am_user,
            data={'name': settings.PUBLIC_ACCESS_TAGNAME})
        # Check response and data
        self.assertEqual(response.status_code, 201)
        self.assertIn(response.data['name'], settings.PUBLIC_ACCESS_TAGNAME)

    def test_lvem_user_tag_log(self):
        """LV-EM user can't tag logs for any superevents"""
        # Internal-only superevent (no tags)
        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'name': self.tag1.name})
        # Check response and data - 404 due to superevent not included in
        # full queryset
        self.assertEqual(response.status_code, 404)

        # Internal-only superevent again, with tag already applied,
        # to make sure error message is what we expect and that nothing
        # leaks out that way.
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id,
            self.internal_superevent_exposed_log.N])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'name': self.tag1.name})
        # Check response and data
        self.assertEqual(response.status_code, 404)

        # LV-EM exposed superevent
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.lvem_superevent.superevent_id,
            self.lvem_superevent_exposed_log.N])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'name': self.tag1.name})
        # Check response and data
        self.assertEqual(response.status_code, 403)

    def test_public_user_tag_log(self):
        """Public user can't tag any logs"""
        # Internal-only superevent (no tags)
        # Create a new log
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.internal_superevent, comment='test')

        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id, log.N])
        response = self.request_as_user(url, "POST",
            data={'name': self.tag1.name})
        # Check response and data - 404 due to superevent not included in
        # full queryset
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

        # Internal-only superevent again, with tag already applied,
        # to make sure error message is what we expect and that nothing
        # leaks out that way.
        url = v_reverse('superevents:superevent-log-tag-list',
            args=[self.internal_superevent.superevent_id,
            self.internal_superevent_exposed_log.N])
        response = self.request_as_user(url, "POST",
            data={'name': self.tag1.name})
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

        # Test publicly-exposed superevent
        # TODO


class TestSupereventLogTagDetail(AccessManagersGroupAndUserSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventLogTagDetail, cls).setUpTestData()

        # Add logs to superevents
        cls.num_logs = 3
        for i in range(cls.num_logs):
            Log.objects.create(superevent=cls.internal_superevent,
                issuer=cls.internal_user, comment='test comment')
            Log.objects.create(superevent=cls.lvem_superevent,
                issuer=cls.internal_user, comment='test comment')

        # Expose one log on each superevent to LV-EM and store them on the
        # class for easy access
        cls.internal_superevent_exposed_log = cls.internal_superevent \
            .log_set.first()
        cls.lvem_superevent_exposed_log = cls.lvem_superevent \
            .log_set.first()
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.internal_superevent_exposed_log)
        assign_perm('superevents.view_log', cls.lvem_group,
            obj=cls.lvem_superevent_exposed_log)
        # TODO: expose one log on each superevent to public

        # Create some tags
        cls.tag1 = Tag.objects.create(name='test_tag1')
        cls.tag2 = Tag.objects.create(name='test_tag2')
        cls.lvem_tag = Tag.objects.create(
            name=settings.EXTERNAL_ACCESS_TAGNAME)
        cls.public_tag = Tag.objects.create(
            name=settings.PUBLIC_ACCESS_TAGNAME)

        # Add tags to the exposed logs
        cls.internal_superevent_exposed_log.tags.add(*(cls.tag1, cls.tag2))
        cls.lvem_superevent_exposed_log.tags.add(*(cls.tag1, cls.tag2))

    def test_internal_user_get(self):
        """Internal user can get all tags for all logs for all superevents"""
        for s in Superevent.objects.all():
            for l in s.log_set.all():
                for t in l.tags.all():
                    url = reverse(('api:default:superevents:'
                        'superevent-log-tag-detail'),
                        args=[s.superevent_id, l.N, t.name])
                    response = self.request_as_user(url, "GET",
                        self.internal_user)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data['name'], t.name)

    def test_lvem_user_get_tags_for_hidden_superevent(self):
        """LV-EM user can't get tags for any logs on hidden superevent"""
        for l in self.internal_superevent.log_set.all():
            for t in l.tags.all():
                url = reverse(('api:default:superevents:'
                    'superevent-log-tag-detail'),
                    args=[self.internal_superevent.superevent_id, l.N, t.name])
                response = self.request_as_user(url, "GET", self.lvem_user)
                self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_tags_for_exposed_superevent(self):
        """
        LV-EM user can only get tags for exposed logs on exposed superevent
        """
        for l in self.lvem_superevent.log_set.all():
            for t in l.tags.all():
                url = reverse(('api:default:superevents:'
                    'superevent-log-tag-detail'),
                    args=[self.lvem_superevent.superevent_id, l.N, t.name])
                response = self.request_as_user(url, "GET", self.lvem_user)
                if (l == self.lvem_superevent_exposed_log):
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data['name'], t.name)
                else:
                    self.assertEqual(response.status_code, 404)

    def test_public_user_get_tags_for_hidden_superevent(self):
        """Public user can't get tags for any logs for hidden superevent"""
        for l in self.internal_superevent.log_set.all():
            for t in l.tags.all():
                url = reverse(('api:default:superevents:'
                    'superevent-log-tag-detail'),
                    args=[self.internal_superevent.superevent_id, l.N, t.name])
                response = self.request_as_user(url, "GET")
                self.assertEqual(response.status_code, 403)
                # TODO: this will be 404 in the future

    def test_public_user_get_tags_for_exposed_superevent(self):
        """
        Public user can only get tags for exposed logs on exposed superevent
        """
        # TODO
        pass

    def test_internal_user_remove_tag(self):
        """Internal user can remove tags from superevent logs"""
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.internal_superevent.superevent_id,
            self.internal_superevent_exposed_log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 204)

    def test_internal_user_remove_lvem_tag(self):
        """Internal user can't remove lvem tag from superevent logs"""
        # Add lvem tag to a log
        log = self.internal_superevent.log_set.first()
        log.tags.add(self.lvem_tag)

        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[log.superevent.superevent_id, log.N, self.lvem_tag.name])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_internal_user_remove_public_tag(self):
        """Internal user can't remove public tag from superevent logs"""
        # Add public tag to a log
        log = self.internal_superevent.log_set.first()
        log.tags.add(self.public_tag)

        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[log.superevent.superevent_id, log.N, self.public_tag.name])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_access_manager_remove_lvem_tag(self):
        """Access manager can remove lvem tag from superevent logs"""
        # Add lvem tag to a log
        log = self.internal_superevent.log_set.first()
        log.tags.add(self.lvem_tag)

        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[log.superevent.superevent_id, log.N, self.lvem_tag.name])
        response = self.request_as_user(url, "DELETE", self.am_user)
        self.assertEqual(response.status_code, 204)

    def test_access_manager_remove_public_tag(self):
        """Access manager can remove public tag from superevent logs"""
        # Add lvem tag to a log
        log = self.internal_superevent.log_set.first()
        log.tags.add(self.public_tag)

        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[log.superevent.superevent_id, log.N, self.public_tag.name])
        response = self.request_as_user(url, "DELETE", self.am_user)
        self.assertEqual(response.status_code, 204)

    def test_lvem_user_remove_tag_from_log_on_hidden_superevent(self):
        """LV-EM user can't remove tag from logs on hidden superevent"""
        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.internal_superevent.superevent_id,
            self.internal_superevent_exposed_log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_remove_tag_from_log_on_exposed_superevent(self):
        """LV-EM user can't remove tag from logs on exposed superevent"""
        # Hidden log on exposed superevent, no tags
        log = Log.objects.create(issuer=self.internal_user,
            superevent=self.lvem_superevent, comment='test')
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.lvem_superevent.superevent_id, log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Add the tag and try again just to make sure
        log.tags.add(self.tag1)
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.lvem_superevent.superevent_id, log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Exposed log on exposed superevent
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.lvem_superevent.superevent_id,
            self.lvem_superevent_exposed_log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_remove_tag_from_log_on_hidden_superevent(self):
        """Public user can't remove tag from logs on hidden superevent"""
        # Make request and check response data
        url = v_reverse('superevents:superevent-log-tag-detail',
            args=[self.internal_superevent.superevent_id,
            self.internal_superevent_exposed_log.N, self.tag1.name])
        response = self.request_as_user(url, "DELETE")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

    def test_public_user_remove_tag_from_log_on_exposed_superevent(self):
        """Public user can't remove tag from logs on exposed superevent"""
        # TODO
        pass


class TestSupereventVOEventList(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventVOEventList, cls).setUpTestData()

        # Create simple VOEvents
        voevent1 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.internal_superevent, voevent_type='IN')
        voevent2 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.internal_superevent, voevent_type='UP')
        voevent3 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.lvem_superevent, voevent_type='IN')
        voevent4 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.lvem_superevent, voevent_type='UP')

        # Need the 'em_follow' tag since it is automatically applied
        # to voevent-related log messages
        Tag.objects.get_or_create(name='em_follow')

    @classmethod
    def setUpClass(cls):
        super(TestSupereventVOEventList, cls).setUpClass()

        # Define VOEvent data for POST-ing
        cls.voevent_data = {
            'voevent_type': VOEvent.VOEVENT_TYPE_PRELIMINARY,
            'internal': True,
            'vetted': False,
            'open_alert': False,
            'hardware_inj': False,
            'CoincComment': False,
        }

    def test_internal_user_get_list(self):
        """Internal user can get all VOEvents for all superevents"""
        for s in Superevent.objects.all():
            url = v_reverse('superevents:superevent-voevent-list',
                args=[s.superevent_id])
            response = self.request_as_user(url, "GET", self.internal_user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['voevents']),
                s.voevent_set.count())

            # Check individual voevent presence by N values
            voevent_nums = [v['N'] for v in response.data['voevents']]
            for v in s.voevent_set.all():
                self.assertIn(v.N, voevent_nums)

    def test_lvem_user_get_list_for_hidden_superevent(self):
        """LV-EM user can't get any VOEvents for hidden superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_list_for_exposed_superevent(self):
        """LV-EM user can get all VOEvents for exposed superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['voevents']),
            self.lvem_superevent.voevent_set.count())
        # Check individual voevent presence by N values
        voevent_nums = [v['N'] for v in response.data['voevents']]
        for v in self.lvem_superevent.voevent_set.all():
            self.assertIn(v.N, voevent_nums)

    def test_public_user_get_list_for_hidden_superevent(self):
        """Public user can't get any VOEvents for hidden superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

    def test_public_user_get_list_for_exposed_superevent(self):
        """Public user can get all VOEvents for exposed superevents"""
        # TODO
        pass

    def test_internal_user_create_voevent(self):
        """Internal user can create VOEvents for all superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.voevent_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['voevent_type'],
            self.voevent_data['voevent_type'])

    def test_lvem_user_create_voevent_for_hidden_superevent(self):
        """LV-EM user can't create VOEvents for hidden superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.voevent_data)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_create_voevent_for_exposed_superevent(self):
        """LV-EM user can't create VOEvents for exposed superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.voevent_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to create VOEvents',
            response.data['detail'])

    def test_public_user_create_voevent_for_hidden_superevent(self):
        """Public user can't create VOEvents for hidden superevents"""
        url = v_reverse('superevents:superevent-voevent-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", data=self.voevent_data)
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

    def test_public_user_create_voevent_for_exposed_superevent(self):
        """Public user can't create VOEvents for exposed superevents"""
        # TODO
        pass


class TestSupereventVOEventDetail(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventVOEventDetail, cls).setUpTestData()

        # Create simple VOEvents
        voevent1 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.internal_superevent, voevent_type='IN')
        voevent2 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.internal_superevent, voevent_type='UP')
        voevent3 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.lvem_superevent, voevent_type='IN')
        voevent4 = VOEvent.objects.create(issuer=cls.internal_user,
            superevent=cls.lvem_superevent, voevent_type='UP')

    def test_internal_user_get_detail(self):
        """Internal user can get all VOEvent details for all superevents"""
        for s in Superevent.objects.all():
            for v in s.voevent_set.all():
                url = reverse(('api:default:superevents:'
                    'superevent-voevent-detail'),
                    args=[s.superevent_id, v.N])
                response = self.request_as_user(url, "GET", self.internal_user)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['N'], v.N)
                self.assertEqual(response.data['voevent_type'], v.voevent_type)

    def test_lvem_user_get_detail_for_hidden_superevent(self):
        """LV-EM user can't get VOEvent detail for hidden superevents"""
        voevent = self.internal_superevent.voevent_set.first()
        url = v_reverse('superevents:superevent-voevent-detail',
            args=[self.internal_superevent.superevent_id, voevent.N])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_detail_for_exposed_superevent(self):
        """LV-EM user can get all VOEvent details for exposed superevents"""
        for v in self.lvem_superevent.voevent_set.all():
            url = v_reverse('superevents:superevent-voevent-detail',
                args=[self.lvem_superevent.superevent_id, v.N])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['N'], v.N)
            self.assertEqual(response.data['voevent_type'], v.voevent_type)

    def test_public_user_get_list_for_hidden_superevent(self):
        """Public user can't get any VOEvent details for hidden superevents"""
        v = self.internal_superevent.voevent_set.first()
        url = v_reverse('superevents:superevent-voevent-detail',
            args=[self.internal_superevent.superevent_id, v.N])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

    def test_public_user_get_list_for_exposed_superevent(self):
        """Public user can get all VOEvent details for exposed superevents"""
        # TODO: should this be the case?
        pass


class TestSupereventEMObservationList(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventEMObservationList, cls).setUpTestData()

        # Create a temporary EMGroup
        cls.emgroup = EMGroup.objects.create(name=cls.emgroup_name)

        # Create simple EMObservations
        emo1 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.internal_superevent, group=cls.emgroup)
        emo2 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.internal_superevent, group=cls.emgroup)
        emo3 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.lvem_superevent, group=cls.emgroup)
        emo4 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.lvem_superevent, group=cls.emgroup)

    @classmethod
    def setUpClass(cls):
        super(TestSupereventEMObservationList, cls).setUpClass()

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

    def test_internal_user_get_list(self):
        """Internal user can get all EMObservations for all superevents"""
        for s in Superevent.objects.all():
            url = reverse(('api:default:superevents:'
                'superevent-emobservation-list'),
                args=[s.superevent_id])
            response = self.request_as_user(url, "GET", self.internal_user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['observations']),
                s.emobservation_set.count())

            # Check individual voevent presence by N values
            emo_nums = [emo['N'] for emo in response.data['observations']]
            for emo in s.emobservation_set.all():
                self.assertIn(emo.N, emo_nums)

    def test_lvem_user_get_list_for_hidden_superevent(self):
        """LV-EM user can't get any EMObservations for hidden superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_list_for_exposed_superevent(self):
        """LV-EM user can get all EMObservations for exposed superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['observations']),
            self.lvem_superevent.emobservation_set.count())
        # Check individual voevent presence by N values
        emo_nums = [emo['N'] for emo in response.data['observations']]
        for emo in self.lvem_superevent.emobservation_set.all():
            self.assertIn(emo.N, emo_nums)

    def test_public_user_get_list_for_hidden_superevent(self):
        """Public user can't get any EMObservations for hidden superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

    def test_public_user_get_list_for_exposed_superevent(self):
        """Public user can get all EMObservations for exposed superevents"""
        # TODO: do we really want this to be the case?
        pass

    def test_internal_user_create_emobservation(self):
        """Internal user can create EMObservations for all superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.emobservation_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['comment'],
            self.emobservation_data['comment'])
        self.assertEqual(response.data['group'],
            self.emobservation_data['group'])

    def test_lvem_user_create_emobservation_for_hidden_superevent(self):
        """LV-EM user can't create EMObservations for hidden superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.emobservation_data)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_create_emobservation_for_exposed_superevent(self):
        """LV-EM user can create EMObservations for exposed superevents"""
        # Have to create lvem tag since there will be a log created to
        # document the EMObservation creation and it will be tagged
        # with 'lvem' since it was created by an external user.
        Tag.objects.create(name=settings.EXTERNAL_ACCESS_TAGNAME)
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.emobservation_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['comment'],
            self.emobservation_data['comment'])
        self.assertEqual(response.data['group'],
            self.emobservation_data['group'])

    def test_public_user_create_emobservation_for_hidden_superevent(self):
        """Public user can't create EMObservations for hidden superevents"""
        url = v_reverse('superevents:superevent-emobservation-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST",
            data=self.emobservation_data)
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

    def test_public_user_create_emobservation_for_exposed_superevent(self):
        """Public user can't create EMObservation for exposed superevents"""
        # TODO
        pass


class TestSupereventEMObservationDetail(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventEMObservationDetail, cls).setUpTestData()

        # Create a temporary EMGroup
        cls.emgroup = EMGroup.objects.create(name='fake_emgroup')

        # Create simple EMObservations
        emo1 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.internal_superevent, group=cls.emgroup)
        emo2 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.internal_superevent, group=cls.emgroup)
        emo3 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.lvem_superevent, group=cls.emgroup)
        emo4 = EMObservation.objects.create(submitter=cls.internal_user,
            superevent=cls.lvem_superevent, group=cls.emgroup)

    def test_internal_user_get_detail(self):
        """Internal user can get EMObservaion details for all superevents"""
        for s in Superevent.objects.all():
            for emo in s.emobservation_set.all():
                url = reverse(('api:default:superevents:'
                    'superevent-emobservation-detail'),
                    args=[s.superevent_id, emo.N])
                response = self.request_as_user(url, "GET", self.internal_user)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['N'], emo.N)

    def test_lvem_user_get_detail_for_hidden_superevent(self):
        """LV-EM user can't get EMObservation detail for hidden superevents"""
        emo = self.internal_superevent.emobservation_set.first()
        url = v_reverse('superevents:superevent-emobservation-detail',
            args=[self.internal_superevent.superevent_id, emo.N])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get_detail_for_exposed_superevent(self):
        """LV-EM user can get EMObservation details for exposed superevents"""
        for emo in self.lvem_superevent.emobservation_set.all():
            url = reverse(('api:default:superevents:'
                'superevent-emobservation-detail'),
                args=[self.lvem_superevent.superevent_id, emo.N])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['N'], emo.N)
            self.assertEqual(response.data['group'], emo.group.name)

    def test_public_user_get_detail_for_hidden_superevent(self):
        """
        Public user can't get any EMObservation details for hidden superevents
        """
        emo = self.internal_superevent.emobservation_set.first()
        url = reverse(('api:default:superevents:'
            'superevent-emobservation-detail'),
            args=[self.internal_superevent.superevent_id, emo.N])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future

    def test_public_user_get_detail_for_exposed_superevent(self):
        """
        Public user can get all EMObservation details for exposed superevents
        """
        # TODO: should this be the case?
        pass


class TestSupereventFileList(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventFileList, cls).setUpTestData()

        # Create files for internal superevent
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

    def test_internal_get_file_list_for_superevent(self):
        """Internal user can see all files for all superevents"""
        for s in Superevent.objects.all():
            url = v_reverse('superevents:superevent-file-list',
                args=[s.superevent_id])
            response = self.request_as_user(url, "GET", self.internal_user)
            self.assertEqual(response.status_code, 200)
            # Expected list of file names, including symlinks to top version
            file_logs = s.log_set.exclude(filename='')
            file_list = [l.versioned_filename for l in file_logs]
            symlinks = list(set([fl.filename for fl in file_logs]))
            file_list.extend(symlinks)
            self.assertEqual(len(file_list), len(response.data))
            for f in file_list:
                self.assertIn(f, response.data)

    def test_lvem_get_file_list_for_hidden_superevent(self):
        """LV-EM user can't get file list for hidden superevents"""
        url = v_reverse('superevents:superevent-file-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

        # Try exposing a log and make sure it's still a 404
        log = self.internal_superevent.log_set.exclude(filename='').first()
        expose_log_to_lvem(log)
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_file_list_for_exposed_superevent(self):
        """LV-EM user can get exposed file list for exposed superevents"""
        # Expose a non-symlinked log
        log = self.lvem_superevent.log_set.get(filename=self.file1['filename'],
            file_version=1)
        expose_log_to_lvem(log)

        # Make request and check response
        url = v_reverse('superevents:superevent-file-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn(log.versioned_filename, response.data)

    def test_lvem_get_file_list_for_exposed_superevent_symlinked_file(self):
        """
        LV-EM user can get exposed file list for exposed superevents, including
        symlinks
        """
        # Expose the most recent version of a file, make sure both the
        # versioned file and non-versioned symlink are shown
        log = self.lvem_superevent.log_set.get(filename=self.file1['filename'],
            file_version=3)
        expose_log_to_lvem(log)

        # Make request and get response
        url = v_reverse('superevents:superevent-file-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertIn(log.versioned_filename, response.data)
        self.assertIn(log.filename, response.data)

    def test_public_get_file_list_for_hidden_superevent(self):
        """Public user can't get file list for hidden superevents"""
        url = v_reverse('superevents:superevent-file-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 error in the future

        # Try exposing a log and make sure it's still a 404
        log = self.internal_superevent.log_set.exclude(filename='').first()
        expose_log_to_public(log)
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 error in the future

    def test_public_get_file_list_for_exposed_superevent(self):
        """Public user can get exposed file list for exposed superevents"""
        # TODO

    def test_public_get_file_list_for_exposed_superevent_symlinked_file(self):
        """
        Public user can get exposed file list for exposed superevents, including
        symlinks
        """
        # TODO


class TestSupereventFileDetail(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventFileDetail, cls).setUpTestData()

        # Create files for internal superevent
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

    def test_internal_get_file_detail_for_superevent(self):
        """Internal user can see all files for all superevents"""
        for s in Superevent.objects.all():
            file_logs = s.log_set.exclude(filename='')
            file_list = [l.versioned_filename for l in file_logs]
            symlinks = list(set([fl.filename for fl in file_logs]))
            file_list.extend(symlinks)
            for f in file_list:
                url = v_reverse('superevents:superevent-file-detail',
                    args=[s.superevent_id, f])
                response = self.request_as_user(url, "GET", self.internal_user)
                self.assertEqual(response.status_code, 200)

    def test_lvem_get_file_detail_for_hidden_superevent(self):
        """LV-EM user can't get file detail for hidden superevents"""
        file_logs = self.internal_superevent.log_set.exclude(filename='')
        file_list = [l.versioned_filename for l in file_logs]
        symlinks = list(set([fl.filename for fl in file_logs]))
        file_list.extend(symlinks)
        for f in file_list:
            url = v_reverse('superevents:superevent-file-detail',
                args=[self.internal_superevent.superevent_id, f])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 404)

    def test_lvem_get_file_detail_for_exposed_superevent(self):
        """LV-EM user can get only exposed files for exposed superevents"""
        # Expose a non-symlinked log
        log = self.lvem_superevent.log_set.get(filename=self.file1['filename'],
            file_version=1)
        expose_log_to_lvem(log)

        # Make request and check response
        url = v_reverse('superevents:superevent-file-detail',
            args=[self.lvem_superevent.superevent_id, log.versioned_filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        data1 = response.data

        # Try with a different version (not exposed)
        log2 = self.lvem_superevent.log_set.get(filename=
            self.file1['filename'], file_version=0)
        # Make request and check response
        url = v_reverse('superevents:superevent-file-detail',
            args=[self.lvem_superevent.superevent_id, log2.versioned_filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_file_detail_for_exposed_superevent_symlinked_file(self):
        """
        LV-EM user can get exposed files for exposed superevents, including
        symlinks
        """
        # Expose a non-symlinked log
        log = self.lvem_superevent.log_set.get(filename=self.file1['filename'],
            file_version=3)
        expose_log_to_lvem(log)

        # Make request and check response
        url = v_reverse('superevents:superevent-file-detail',
            args=[self.lvem_superevent.superevent_id, log.versioned_filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        data1 = response.data

        # Repeat with non-versioned filename
        url = v_reverse('superevents:superevent-file-detail',
            args=[self.lvem_superevent.superevent_id, log.filename])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, data1)

    def test_public_get_file_detail_for_hidden_superevent(self):
        """Public user can't get files for hidden superevents"""
        file_logs = self.internal_superevent.log_set.exclude(filename='')
        file_list = [l.versioned_filename for l in file_logs]
        symlinks = list(set([fl.filename for fl in file_logs]))
        file_list.extend(symlinks)
        for f in file_list:
            url = v_reverse('superevents:superevent-file-detail',
                args=[self.internal_superevent.superevent_id, f])
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)
            # TODO: will be 404 in the future

    def test_public_get_file_detail_for_exposed_superevent(self):
        """Public user can get exposed files for exposed superevents"""
        # TODO

    def test_public_get_file_detail_for_exposed_superevent_symlinked_file(self):
        """
        Public user can get exposed files for exposed superevents, including
        symlinks
        """
        # TODO


class TestSupereventGroupObjectPermissionList(SupereventSetup,
    GraceDbApiTestBase):

    def test_internal_user_get_permissions(self):
        """Internal user can view permissions list for all superevents"""
        # Internal
        url = v_reverse('superevents:superevent-permission-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Check response and data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['permissions'], [])

        # Exposed
        url = v_reverse('superevents:superevent-permission-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Check response and data
        data = response.data['permissions']
        groups = [p['group'] for p in data]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 3)
        self.assertEqual(groups.count(settings.PUBLIC_GROUP), 1)
        self.assertEqual(groups.count(settings.LVEM_OBSERVERS_GROUP), 2)

    def test_lvem_user_get_permissions(self):
        """LV-EM user can't get permission list"""
        # Internal
        url = v_reverse('superevents:superevent-permission-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        # Check response and data
        self.assertEqual(response.status_code, 404)

        # Exposed
        url = v_reverse('superevents:superevent-permission-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        # Check response and data
        self.assertEqual(response.status_code, 403)

    def test_public_user_get_permissions(self):
        """Public user can't get permission list"""
        # Internal
        url = v_reverse('superevents:superevent-permission-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

        # Exposed: TODO


class TestSupereventGroupObjectPermissionModify(SupereventSetup,
    AccessManagersGroupAndUserSetup, GraceDbApiTestBase):

    def test_internal_user_expose_internal_superevent(self):
        """Internal user can't modify permissions to expose superevent"""
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'action': 'expose'})
        # Check response
        self.assertEqual(response.status_code, 403)
        self.assertIn('not allowed to expose superevents',
            response.data['detail'])

    def test_internal_user_hide_exposed_superevent(self):
        """Internal user can't modify permissions to hide superevent"""
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data={'action': 'hide'})
        # Check response
        self.assertEqual(response.status_code, 403)
        self.assertIn('not allowed to hide superevents',
            response.data['detail'])

    def test_access_manager_expose_internal_superevent(self):
        """Access manager can modify permissions to expose superevent"""
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.am_user,
            data={'action': 'expose'})
        # Check response
        groups = [p['group'] for p in response.data]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(groups.count(settings.PUBLIC_GROUP), 1)
        self.assertEqual(groups.count(settings.LVEM_OBSERVERS_GROUP), 2)

    def test_access_manager_hide_exposed_superevent(self):
        """Access manager can modify permissions to hide superevent"""
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.am_user,
            data={'action': 'hide'})
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_lvem_user_permissions_modify(self):
        """LV-EM user can't modify permissions"""
        # Internal - expose
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'action': 'expose'})
        # Check response and data
        self.assertEqual(response.status_code, 404)

        # Exposed
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data={'action': 'hide'})
        # Check response and data
        self.assertEqual(response.status_code, 403)

    def test_public_user_get_permissions(self):
        # Internal
        url = v_reverse('superevents:superevent-permission-modify',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        # Check response and data
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

        # Exposed: TODO


class TestSupereventSignoffList(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventSignoffList, cls).setUpTestData()

        # Create signoffs for superevents
        cls.internal_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        cls.lvem_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.lvem_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)

    def test_internal_get_signoff_list(self):
        """Internal user can view list of signoffs"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['signoffs']),
            self.internal_superevent.signoff_set.count())

    def test_lvem_get_hidden_signoff_list(self):
        """LV-EM user can't view list of signoffs for hidden superevent"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_get_exposed_signoff_list(self):
        """LV-EM user can't view list of signoffs for exposed superevent"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to view superevent signoffs',
            response.data['detail'])

    def test_public_get_hidden_signoff_list(self):
        """Public user can't view list of signoffs for hidden superevent"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 error in the future

    def test_public_get_exposed_signoff_list(self):
        """Public user can't view list of signoffs for exposed superevent"""
        # TODO
        pass


class TestSupereventSignoffDetail(SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventSignoffDetail, cls).setUpTestData()

        # Create signoffs for superevents
        cls.internal_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        cls.lvem_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.lvem_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)

    def test_internal_user_get_signoff_detail(self):
        """Internal user can view signoff detail"""
        signoff = self.internal_superevent.signoff_set.first()
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['submitter'],
            signoff.submitter.username)
        self.assertEqual(response.data['signoff_type'], signoff.signoff_type)
        self.assertEqual(response.data['status'], signoff.status)
        self.assertEqual(response.data['comment'], signoff.comment)
        self.assertEqual(response.data['instrument'], signoff.instrument)

    def test_lvem_user_get_signoff_detail_for_hidden_superevent(self):
        """LV-EM user can't view signoff detail for hidden superevent"""
        signoff = self.internal_superevent.signoff_set.first()
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 404)
        
    def test_lvem_user_get_signoff_detail_for_exposed_superevent(self):
        """LV-EM user can't view signoff detail for exposed superevent"""
        signoff = self.lvem_superevent.signoff_set.first()
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.lvem_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        
    def test_public_user_get_signoff_detail_for_hidden_superevent(self):
        """Public user can't view signoff detail for hidden superevent"""
        signoff = self.internal_superevent.signoff_set.first()
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
        # TODO: will be 404 in the future
        
    def test_public_user_get_signoff_detail_for_exposed_superevent(self):
        """Public user can't view signoff detail for exposed superevent"""
        # TODO
        pass


class TestSupereventSignoffCreation(SignoffGroupsAndUsersSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventSignoffCreation, cls).setUpTestData()

        # Create a few labels for testing
        h1ops, _ =Label.objects.get_or_create(name='H1OPS')
        Label.objects.get_or_create(name='H1OK')
        Label.objects.get_or_create(name='H1NO')
        advreq, _ = Label.objects.get_or_create(name='ADVREQ')
        Label.objects.get_or_create(name='ADVOK')
        Label.objects.get_or_create(name='ADVNO')

        # Add H1OPS and ADVREQ to superevents so that signoffs can be created
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=h1ops, creator=cls.internal_user)
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=advreq, creator=cls.internal_user)

        # Also need em_follow tag since signoff-related log messages are
        # tagged with it
        Tag.objects.get_or_create(name='em_follow')

    @classmethod
    def setUpClass(cls):
        super(TestSupereventSignoffCreation, cls).setUpClass()

        # Data for signoff creation
        cls.signoff_data = {
            'signoff_type': Signoff.SIGNOFF_TYPE_OPERATOR,
            'status': Signoff.OPERATOR_STATUS_NOTOK,
            'instrument': Signoff.INSTRUMENT_H1,
            'comment': 'test comment',
        }

    def test_internal_user_create_signoff(self):
        """Basic internal user can't create signoffs"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to create superevent signoffs',
            response.data['detail'])

    def test_H1_control_room_create_H1_signoff(self):
        """H1 control room user can create H1 signoffs"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.H1_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], self.signoff_data['status'])
        self.assertEqual(response.data['comment'],
            self.signoff_data['comment'])

    def test_H1_control_room_create_other_signoff(self):
        """H1 control room user can't create signoffs for other ifos"""
        self.signoff_data['instrument'] = Signoff.INSTRUMENT_L1
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.H1_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to do L1 signoffs',
            response.data['detail'])

    def test_advocate_create_adv_signoff(self):
        """EM advocate user can create advocate signoffs"""
        self.signoff_data['instrument'] = ''
        self.signoff_data['signoff_type'] = Signoff.SIGNOFF_TYPE_ADVOCATE
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.adv_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], self.signoff_data['status'])
        self.assertEqual(response.data['comment'],
            self.signoff_data['comment'])

    def test_lvem_user_create_signoff_for_hidden_superevent(self):
        """LV-EM user can't create signoffs for hidden superevents"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_create_signoff_for_exposed_superevent(self):
        """LV-EM user can't create signoffs for exposed superevents"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.lvem_superevent.superevent_id])
        response = self.request_as_user(url, "POST", self.lvem_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to create superevent signoffs',
            response.data['detail'])

    def test_public_user_create_signoff_for_hidden_superevent(self):
        """Public user can't create signoffs for hidden superevents"""
        url = v_reverse('superevents:superevent-signoff-list',
            args=[self.internal_superevent.superevent_id])
        response = self.request_as_user(url, "POST", data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

    def test_public_user_create_signoff_for_exposed_superevent(self):
        """Public user can't create signoffs for exposed superevents"""
        # TODO
        pass


class TestSupereventSignoffUpdate(SignoffGroupsAndUsersSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventSignoffUpdate, cls).setUpTestData()

        # Create signoffs for superevents
        cls.internal_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        cls.lvem_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.lvem_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)

        # Create a few labels for testing
        Label.objects.get_or_create(name='H1OPS')
        h1ok, _ = Label.objects.get_or_create(name='H1OK')
        Label.objects.get_or_create(name='H1NO')
        Label.objects.get_or_create(name='ADVREQ')
        advok, _ = Label.objects.get_or_create(name='ADVOK')
        Label.objects.get_or_create(name='ADVNO')

        # Add H1OPS and ADVREQ to superevents so that signoffs can be created
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=h1ok, creator=cls.internal_user)
        Labelling.objects.create(superevent=cls.lvem_superevent,
            label=h1ok, creator=cls.internal_user)
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=advok, creator=cls.internal_user)

        # Also need em_follow tag since signoff-related log messages are
        # tagged with it
        Tag.objects.get_or_create(name='em_follow')

    @classmethod
    def setUpClass(cls):
        super(TestSupereventSignoffUpdate, cls).setUpClass()

        # Data for signoff creation
        cls.signoff_data = {
            'status': Signoff.OPERATOR_STATUS_NOTOK,
            'comment': 'test comment',
        }

    def test_internal_user_update_signoff(self):
        """Basic internal user can't update signoffs"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.internal_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to change superevent signoffs',
            response.data['detail'])

    def test_H1_control_room_update_H1_signoff(self):
        """H1 control room user can update H1 signoffs"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.H1_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], self.signoff_data['status'])
        self.assertEqual(response.data['comment'],
            self.signoff_data['comment'])

    def test_H1_control_room_update_other_signoff(self):
        """H1 control room user can't update signoffs for other ifos"""
        signoff = Signoff.objects.create(submitter=self.internal_user,
            superevent=self.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_L1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.H1_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to do L1 signoffs',
            response.data['detail'])

    def test_advocate_update_adv_signoff(self):
        """EM advocate user can update advocate signoffs"""
        signoff = Signoff.objects.create(submitter=self.internal_user,
            superevent=self.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument="", signoff_type=Signoff.SIGNOFF_TYPE_ADVOCATE)
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.adv_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], self.signoff_data['status'])
        self.assertEqual(response.data['comment'],
            self.signoff_data['comment'])

    def test_lvem_user_update_signoff_for_hidden_superevent(self):
        """LV-EM user can't update signoffs for hidden superevents"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.lvem_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_update_signoff_for_exposed_superevent(self):
        """LV-EM user can't update signoffs for exposed superevents"""
        signoff = self.lvem_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", self.lvem_user,
            data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to change superevent signoffs',
            response.data['detail'])

    def test_public_user_update_signoff_for_hidden_superevent(self):
        """Public user can't update signoffs for hidden superevents"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "PATCH", data=self.signoff_data)
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

    def test_public_user_update_signoff_for_exposed_superevent(self):
        """Public user can't update signoffs for exposed superevents"""
        # TODO
        pass


class TestSupereventSignoffDeletion(SignoffGroupsAndUsersSetup,
    SupereventSetup, GraceDbApiTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestSupereventSignoffDeletion, cls).setUpTestData()

        # Create signoffs for superevents
        cls.internal_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        cls.lvem_signoff = Signoff.objects.create(
            submitter=cls.internal_user, superevent=cls.lvem_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_H1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)

        # Create a few labels for testing
        Label.objects.get_or_create(name='H1OPS')
        h1ok, _ = Label.objects.get_or_create(name='H1OK')
        Label.objects.get_or_create(name='H1NO')
        Label.objects.get_or_create(name='ADVREQ')
        advok, _ = Label.objects.get_or_create(name='ADVOK')
        Label.objects.get_or_create(name='ADVNO')

        # Add H1OPS and ADVREQ to superevents so that signoffs can be created
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=h1ok, creator=cls.internal_user)
        Labelling.objects.create(superevent=cls.lvem_superevent,
            label=h1ok, creator=cls.internal_user)
        Labelling.objects.create(superevent=cls.internal_superevent,
            label=advok, creator=cls.internal_user)

        # Also need em_follow tag since signoff-related log messages are
        # tagged with it
        Tag.objects.get_or_create(name='em_follow')

    def test_internal_user_delete_signoff(self):
        """Basic internal user can't delete signoffs"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.internal_user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to delete superevent signoffs',
            response.data['detail'])

    def test_H1_control_room_delete_H1_signoff(self):
        """H1 control room user can delete H1 signoffs"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[self.internal_superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.H1_user)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, None)

    def test_H1_control_room_delete_other_signoff(self):
        """H1 control room user can't delete signoffs for other ifos"""
        signoff = Signoff.objects.create(submitter=self.internal_user,
            superevent=self.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument=Signoff.INSTRUMENT_L1,
            signoff_type=Signoff.SIGNOFF_TYPE_OPERATOR)
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.H1_user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to do L1 signoffs',
            response.data['detail'])

    def test_advocate_delete_adv_signoff(self):
        """EM advocate user can delete advocate signoffs"""
        signoff = Signoff.objects.create(submitter=self.internal_user,
            superevent=self.internal_superevent,
            status=Signoff.OPERATOR_STATUS_OK,
            instrument="", signoff_type=Signoff.SIGNOFF_TYPE_ADVOCATE)
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.adv_user)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, None)

    def test_lvem_user_delete_signoff_for_hidden_superevent(self):
        """LV-EM user can't delete signoffs for hidden superevents"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_delete_signoff_for_exposed_superevent(self):
        """LV-EM user can't delete signoffs for exposed superevents"""
        signoff = self.lvem_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE", self.lvem_user)
        self.assertEqual(response.status_code, 403)
        self.assertIn('do not have permission to delete superevent signoffs',
            response.data['detail'])

    def test_public_user_delete_signoff_for_hidden_superevent(self):
        """Public user can't delete signoffs for hidden superevents"""
        signoff = self.internal_signoff
        url = v_reverse('superevents:superevent-signoff-detail',
            args=[signoff.superevent.superevent_id,
            signoff.signoff_type + signoff.instrument])
        response = self.request_as_user(url, "DELETE")
        self.assertEqual(response.status_code, 403)
        # TODO: this will be 404 in the future

    def test_public_user_delete_signoff_for_exposed_superevent(self):
        """Public user can't delete signoffs for exposed superevents"""
        # TODO
        pass
