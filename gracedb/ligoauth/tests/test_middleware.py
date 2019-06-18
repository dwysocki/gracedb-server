from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.test.utils import override_settings, modify_settings
from django.urls import reverse

from user_sessions.middleware import SessionMiddleware

from ligoauth.models import AuthGroup
from ligoauth.middleware import (
    ControlRoomMiddleware, ShibbolethWebAuthMiddleware,
)

# See this test class for information about what groups and users
# are already defined for use.
from core.tests.utils import GraceDbTestBase


class TestControlRoomMiddlewareHomeView(GraceDbTestBase):
    """
    Test the behavior of the ControlRoomMiddleware. We run some tests on
    the home page view since operators should be shown a list of
    events needing signoff there, so some context is used that depends
    on the user's membership in a control room group.
    """
    ifo = 'H1'

    @classmethod
    def setUpClass(cls):
        super(TestControlRoomMiddlewareHomeView, cls).setUpClass()
        # Make sure middleware is installed
        if not any(['ControlRoomMiddleware' in m for m in
           settings.MIDDLEWARE]):
            raise ImproperlyConfigured(
                'ControlRoomMiddleware must be installed in MIDDLEWARE')
        cls.url = reverse('home')
        cls.headers = {'REMOTE_ADDR': settings.CONTROL_ROOM_IPS[cls.ifo]}

    @classmethod
    def setUpTestData(cls):
        # Call base class setUpTestData
        super(TestControlRoomMiddlewareHomeView, cls).setUpTestData()

        # Create control room group
        cls.control_room_group, _ = AuthGroup.objects.get_or_create(
            name=cls.ifo.lower() + '_control_room')

    def test_internal_user_in_control_room(self):
        """Internal user in control room is added to control room group"""
        response = self.request_as_user(self.url, "GET", self.internal_user,
            data=None, **self.headers)

        # Ensure that the page is rendered properly, the user is authorized
        # for signoffs, and that the signoff_instrument is correct
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['signoff_authorized'])
        self.assertEqual(response.context['signoff_instrument'], self.ifo)

    def test_internal_user_non_control_room(self):
        """
        Internal user not in control room is not added to control room group
        """
        response = self.request_as_user(self.url, "GET", self.internal_user,
            data=None, **{'REMOTE_ADDR': '1.2.3.4'})

        # Ensure that the page is rendered properly, the user is not authorized
        # for signoffs, and that the signoff_instrument is None
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['signoff_authorized'])
        self.assertTrue(response.context['signoff_instrument'] is None)

    def test_lvem_user_in_control_room(self):
        """LV-EM user in control room is not added to control room group"""
        response = self.request_as_user(self.url, "GET", self.lvem_user,
            data=None, **self.headers)

        # Ensure that the page is rendered properly, the user is not authorized
        # for signoffs, and that the signoff_instrument is None
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['signoff_authorized'])
        self.assertTrue(response.context['signoff_instrument'] is None)

    def test_public_user_in_control_room(self):
        """Public user in control room is not added to control room group"""
        response = self.request_as_user(self.url, "GET", user=None, data=None,
            **self.headers)

        # Ensure that the page is rendered properly, the user is not authorized
        # for signoffs, and that the signoff_instrument is None
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['signoff_authorized'])
        self.assertTrue(response.context['signoff_instrument'] is None)

    def test_inactive_internal_user_in_control_room(self):
        """Inactive internal user in control room is not authenticated"""
        # Set user as inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Make request
        response = self.request_as_user(self.url, "GET", self.internal_user,
            data=None, **self.headers)
        # Should be a 200 response, but with anonymous user
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['signoff_authorized'])
        self.assertTrue(response.context['signoff_instrument'] is None)
        self.assertTrue(response.context['user'].is_anonymous)
        self.assertFalse(response.context['user'].is_authenticated)


class TestControlRoomMiddleware(GraceDbTestBase):
    """
    Test the behavior of the ControlRoomMiddleware directly during the
    request/response cycle in the middleware stack.

    We don't test LV-EM or non-authenticated users here since they
    are booted out initially before request processing.  The tests in this
    class are really just duplicating some of the tests in
    TestControlRoomMiddlewareHomePage anyway, but in a different way.
    """
    ifo = 'H1'

    @classmethod
    def setUpClass(cls):
        # Make sure middleware is installed
        if not any(['ControlRoomMiddleware' in m for m in
           settings.MIDDLEWARE]):
            raise ImproperlyConfigured(
                'ControlRoomMiddleware must be installed in MIDDLEWARE')

        # Requests will be for / by default
        cls.url = reverse('home')

        # Attach request factory to class
        cls.factory = RequestFactory()

        # Set up middleware with fake response handler and attach to class
        cls.mw_instance = ControlRoomMiddleware(lambda r: None)

    @classmethod
    def setUpTestData(cls):
        # Call base class setUpTestData
        super(TestControlRoomMiddleware, cls).setUpTestData()

        # Create control room group
        cls.control_room_group, _ = AuthGroup.objects.get_or_create(
            name=cls.ifo.lower() + '_control_room')

    def test_internal_user_in_control_room(self):
        """Internal user in control room is added to control room group"""
        request = self.factory.get(self.url)
        request.user = self.internal_user
        request.META['REMOTE_ADDR'] = settings.CONTROL_ROOM_IPS[self.ifo]

        # User not in control room group before processing
        self.assertNotIn(self.control_room_group, request.user.groups.all())

        # Process request
        request = self.mw_instance.process_request(request)

        # Test request after processing
        self.assertTrue(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

        # Process response (fake response object since it's not used at all
        # in ControlRoomMiddleware.process_response)
        response = self.mw_instance.process_response(request, None)

        # User not in control room group after response cycle processing
        self.assertFalse(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

    def test_internal_user_non_control_room(self):
        """
        Internal user not in control room is not added to control room group
        """
        request = self.factory.get(self.url)
        request.user = self.internal_user
        request.META['REMOTE_ADDR'] = '1.2.3.4'

        # User not in control room group before processing
        self.assertNotIn(self.control_room_group, request.user.groups.all())

        # Process request
        request = self.mw_instance.process_request(request)

        # Test request after processing
        self.assertFalse(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

        # Process response (fake response object since it's not used at all
        # in ControlRoomMiddleware.process_response)
        response = self.mw_instance.process_response(request, None)

        # User not in control room group after response cycle processing
        self.assertFalse(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

    def test_inactive_internal_user_in_control_room(self):
        """
        Inactive internal user in control room is not added to control room
        group
        """
        # Set user as inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Set up request
        request = self.factory.get(self.url)
        request.user = self.internal_user
        request.META['REMOTE_ADDR'] = settings.CONTROL_ROOM_IPS[self.ifo]

        # User not in control room group before processing
        self.assertFalse(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

        # Process request
        request = self.mw_instance.process_request(request)

        # Test request after processing
        self.assertTrue(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())

        # Process response (fake response object since it's not used at all
        # in ControlRoomMiddleware.process_response)
        response = self.mw_instance.process_response(request, None)

        # User not in control room group after response cycle processing
        self.assertFalse(request.user.groups.filter(
            pk=self.control_room_group.pk).exists())


class TestShibbolethWebAuthMiddleware(GraceDbTestBase):
    """Test authentication using Shibboleth credentials in a web browser"""

    @classmethod
    def setUpClass(cls):
        super(TestShibbolethWebAuthMiddleware, cls).setUpClass()
        # Make sure middleware is installed
        if not any(['ShibbolethWebAuthMiddleware' in m for m in
           settings.MIDDLEWARE]):
            raise ImproperlyConfigured(
                'ShibbolethWebAuthMiddleware must be installed in MIDDLEWARE')

        # Post-login URL for shibboleth attribute ingestion
        cls.url = reverse('post-login')

        # Attach request factory to class
        cls.factory = RequestFactory()

        # Attach middleware to class
        cls.mw_instance = ShibbolethWebAuthMiddleware()

    @classmethod
    def setUpTestData(cls):
        super(TestShibbolethWebAuthMiddleware, cls).setUpTestData()

        # Create robot group
        cls.robot_group = AuthGroup.objects.create(name='robot_accounts',
            ldap_name='robot_accounts_ldap_name')

    def test_internal_user_authentication_post_login(self):
        """
        Internal user can authenticate at post-login view with
        Shibboleth credentials in the request headers
        """
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
        })
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and is who we expect them to be,
        # and that they have the expected group memberships
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(request.user, self.internal_user)
        self.assertTrue(request.user.groups.filter(
            pk=self.internal_group.pk).exists())

    def test_user_authentication_other_url(self):
        """
        No user can authenticate at some other URL, even if
        Shibboleth credentials somehow get in the request headers
        """
        request = self.factory.get(reverse('home'))
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
        })
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # User should not be authenticated
        self.assertFalse(request.user.is_authenticated)
        self.assertTrue(request.user.is_anonymous)
        self.assertFalse(hasattr(request.user, 'backend'))
        self.assertEqual(request.user, AnonymousUser())

    def test_lvem_user_authentication_post_login(self):
        """LV-EM user can authenticate at the post-login URL"""
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.lvem_user.username,
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.ldap_name,
        })
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and is who we expect them to be
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(request.user, self.lvem_user)
        self.assertTrue(request.user.groups.filter(
            pk=self.lvem_obs_group.pk).exists())
        self.assertFalse(request.user.groups.filter(
            pk=self.internal_group.pk).exists())

    def test_public_authentication_post_login(self):
        """User can't be authenticated with no credentials at post-login"""
        request = self.factory.get(self.url)
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # Make sure user is not authenticated and is anonymous,
        # auth backend is not set, and the user has no groups
        self.assertFalse(request.user.is_authenticated)
        self.assertTrue(request.user.is_anonymous)
        self.assertFalse(hasattr(request.user, 'backend'))
        self.assertEqual(request.user.groups.count(), 0)

    def test_internal_user_creation(self):
        """Create new internal user if shib credentials are supplied"""
        new_user_dict = {
            'username': 'new_internal.user',
            'email': 'new_internal.user@group.org',
        }
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: new_user_dict['username'],
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
            settings.SHIB_ATTRIBUTE_MAP['email']: new_user_dict['email'],
        })
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertTrue(request.user.groups.filter(
            pk=self.internal_group.pk).exists())

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertTrue(new_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertEqual(new_user.username, new_user_dict['username'])
        self.assertEqual(new_user.email, new_user_dict['email'])

    def test_lvem_user_creation(self):
        """Create new LV-EM user if shib credentials are supplied"""
        new_user_dict = {
            'username': 'new_lvem.user',
            'email': 'new_lvem.user@group.org',
        }
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: new_user_dict['username'],
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.ldap_name,
            settings.SHIB_ATTRIBUTE_MAP['email']: new_user_dict['email'],
        })
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the LV-EM observers group is
        # attached to the user account
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertTrue(request.user.groups.filter(
            pk=self.lvem_obs_group.pk).exists())

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertTrue(new_user.groups.filter(
            pk=self.lvem_obs_group.pk).exists())
        self.assertEqual(new_user.username, new_user_dict['username'])
        self.assertEqual(new_user.email, new_user_dict['email'])

    def test_group_addition(self):
        """Add a group for a user based on shib group header content"""
        # Create new group for testing
        new_group = AuthGroup.objects.create(name='new_group',
            ldap_name='new_ldap_group')
        # Compile group header
        delim = ShibbolethWebAuthMiddleware.group_delimiter
        groups_str = delim.join([self.internal_group.ldap_name,
            new_group.ldap_name])

        # Set up request
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: groups_str,
        })

        # Make sure user just has internal group initially
        self.assertEqual(self.internal_user.groups.count(), 1)
        self.assertTrue(self.internal_user.groups.filter(
            pk=self.internal_group.pk).exists())

        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        # Process request
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the group memberships are
        # what we expect
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(self.internal_user.groups.count(), 2)
        self.assertTrue(self.internal_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(self.internal_user.groups.filter(
            pk=new_group.pk).exists())

    def test_group_removal(self):
        """Remove a group for a user based on shib group header content"""
        # Create new group, add to user
        new_group = AuthGroup.objects.create(name='new_group',
            ldap_name='new_ldap_group')
        self.internal_user.groups.add(new_group)

        # Set up request
        # Shib session doesn't have new_group in it
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
        })

        # Make sure user has both groups initially
        self.assertEqual(self.internal_user.groups.count(), 2)
        self.assertTrue(self.internal_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(self.internal_user.groups.filter(
            pk=new_group.pk).exists())

        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        # Process request
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the group memberships are
        # what we expect
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(self.internal_user.groups.count(), 1)
        self.assertTrue(self.internal_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertFalse(request.user.groups.filter(
            pk=new_group.pk).exists())

    def test_robotuser_group_addition(self):
        """
        Shib group header content is not used to add groups for a robotuser
        """
        # Create a robot user account
        r_user = User.objects.create(username='robot.user')
        r_user.groups.add(self.internal_group)
        r_user.groups.add(self.robot_group)

        # Create new group for testing
        new_group = AuthGroup.objects.create(name='new_group',
            ldap_name='new_ldap_group')
        # Compile group header
        delim = ShibbolethWebAuthMiddleware.group_delimiter
        groups_str = delim.join([self.internal_group.ldap_name,
            new_group.ldap_name])

        # Set up request
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: r_user.username,
            settings.SHIB_GROUPS_HEADER: groups_str,
        })

        # Make sure user just has internal and robot groups initially
        self.assertEqual(r_user.groups.count(), 2)
        self.assertTrue(r_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=self.robot_group.pk).exists())

        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        # Process request
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the group memberships are
        # unchanged
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(r_user.groups.count(), 2)
        self.assertTrue(r_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=self.robot_group.pk).exists())
        self.assertFalse(r_user.groups.filter(
            pk=new_group.pk).exists())

    def test_robotuser_group_removal(self):
        """
        Shib group header content is not used to remove groups for a robotuser
        """
        # Create a robot user account
        r_user = User.objects.create(username='robot.user')
        r_user.groups.add(self.internal_group)
        r_user.groups.add(self.robot_group)
        # Create new group and add robotuser
        new_group = AuthGroup.objects.create(name='new_group',
            ldap_name='new_ldap_group')
        r_user.groups.add(new_group)

        # Set up request
        # Shib session doesn't have new_group in it
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: r_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
        })

        # Make sure user has three groups initially
        self.assertEqual(r_user.groups.count(), 3)
        self.assertTrue(r_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=self.robot_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=new_group.pk).exists())

        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        # Process request
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the group memberships are
        # unchanged
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertEqual(r_user.groups.count(), 3)
        self.assertTrue(r_user.groups.filter(
            pk=self.internal_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=self.robot_group.pk).exists())
        self.assertTrue(r_user.groups.filter(
            pk=new_group.pk).exists())

    def test_user_update(self):
        """Test user information update in middleware"""
        email1 = 'email1@email.com'
        email2 = 'email2@email.com'
        self.internal_user.email = email1
        self.internal_user.save()

        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
            settings.SHIB_ATTRIBUTE_MAP['email']: email2,
        })

        # Check email just to be sure
        self.assertEqual(email1, self.internal_user.email)

        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        # Process request
        self.mw_instance.process_request(request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')

        # Make sure email is changed as expected
        self.internal_user.refresh_from_db()
        self.assertEqual(email2, self.internal_user.email)


    def test_inactive_internal_user_authentication_post_login(self):
        """
        Inactive internal user can't authenticate at post-login view even
        with Shibboleth credentials in the request headers
        """
        # Set user as inactive
        self.internal_user.is_active = False
        self.internal_user.save(update_fields=['is_active'])

        # Set up request
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.ldap_name,
        })
        # Necessary pre-processing middleware
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        self.mw_instance.process_request(request)

        # User should be anonymous/not authenticated
        self.assertFalse(request.user.is_authenticated)
        self.assertTrue(request.user.is_anonymous)
