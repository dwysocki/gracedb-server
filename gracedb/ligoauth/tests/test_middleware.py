from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup, User, AnonymousUser
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.test.utils import override_settings, modify_settings
from django.urls import reverse

from user_sessions.middleware import SessionMiddleware

from ligoauth.models import RobotUser
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
        self.assertIn(self.control_room_group, request.user.groups.all())

        # Process response (fake response object since it's not used at all
        # in ControlRoomMiddleware.process_response)
        response = self.mw_instance.process_response(request, None)

        # User not in control room group after response cycle processing
        self.assertNotIn(self.control_room_group, request.user.groups.all())

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
        self.assertNotIn(self.control_room_group, request.user.groups.all())

        # Process response (fake response object since it's not used at all
        # in ControlRoomMiddleware.process_response)
        response = self.mw_instance.process_response(request, None)

        # User not in control room group after response cycle processing
        self.assertNotIn(self.control_room_group, request.user.groups.all())


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

    def test_internal_user_authentication_post_login(self):
        """
        Internal user can authenticate at post-login view with
        Shibboleth credentials in the request headers
        """
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
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
        self.assertIn(self.internal_group, request.user.groups.all())

    def test_user_authentication_other_url(self):
        """
        No user can authenticate at some other URL, even if
        Shibboleth credentials somehow get in the request headers
        """
        request = self.factory.get(reverse('home'))
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
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
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.name,
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
        self.assertIn(self.lvem_obs_group, request.user.groups.all())
        self.assertNotIn(self.internal_group, request.user.groups.all())

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
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
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
        self.assertIn(self.internal_group, request.user.groups.all())

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertIn(self.internal_group, new_user.groups.all())
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
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.name,
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
        self.assertIn(self.lvem_obs_group, request.user.groups.all())

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertIn(self.lvem_obs_group, new_user.groups.all())
        self.assertEqual(new_user.username, new_user_dict['username'])
        self.assertEqual(new_user.email, new_user_dict['email'])

    def test_group_addition(self):
        """Add a group for a user based on shib group header content"""
        # Create new group for testing
        new_group = AuthGroup.objects.create(name='new_group')
        # Compile group header
        delim = ShibbolethWebAuthMiddleware.group_delimiter
        groups_str = delim.join([self.internal_group.name, new_group.name])

        # Set up request
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: groups_str,
        })

        # Make sure user just has internal group initially
        self.assertEqual(self.internal_user.groups.count(), 1)
        self.assertIn(self.internal_group, self.internal_user.groups.all())

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
        self.assertIn(self.internal_group, self.internal_user.groups.all())
        self.assertIn(new_group, self.internal_user.groups.all())

    def test_group_removal(self):
        """Remove a group for a user based on shib group header content"""
        # Create new group, add to user
        new_group = AuthGroup.objects.create(name='new_group')
        self.internal_user.groups.add(new_group)

        # Set up request
        # Shib session doesn't have new_group in it
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
        })

        # Make sure user has both groups initially
        self.assertEqual(self.internal_user.groups.count(), 2)
        self.assertIn(self.internal_group, self.internal_user.groups.all())
        self.assertIn(new_group, self.internal_user.groups.all())

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
        self.assertIn(self.internal_group, self.internal_user.groups.all())
        self.assertNotIn(new_group, self.internal_user.groups.all())

    def test_robotuser_group_addition(self):
        """
        Shib group header content is not used to add groups for a robotuser
        """
        # Create a RobotUser and add to internal group
        r_user = RobotUser.objects.create(username='robot.user')
        r_user.groups.add(self.internal_group)

        # Create new group for testing
        new_group = AuthGroup.objects.create(name='new_group')
        # Compile group header
        delim = ShibbolethWebAuthMiddleware.group_delimiter
        groups_str = delim.join([self.internal_group.name, new_group.name])

        # Set up request
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: r_user.username,
            settings.SHIB_GROUPS_HEADER: groups_str,
        })

        # Make sure user just has internal group initially
        self.assertEqual(r_user.groups.count(), 1)
        self.assertIn(self.internal_group, r_user.groups.all())

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
        self.assertEqual(r_user.groups.count(), 1)
        self.assertIn(self.internal_group, r_user.groups.all())
        self.assertNotIn(new_group, r_user.groups.all())

    def test_robotuser_group_removal(self):
        """
        Shib group header content is not used to remove groups for a robotuser
        """
        # Create a RobotUser and add to internal group
        r_user = RobotUser.objects.create(username='robot.user')
        r_user.groups.add(self.internal_group)
        # Create new group and add robotusre
        new_group = AuthGroup.objects.create(name='new_group')
        r_user.groups.add(new_group)

        # Set up request
        # Shib session doesn't have new_group in it
        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: r_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
        })

        # Make sure user has both groups initially
        self.assertEqual(r_user.groups.count(), 2)
        self.assertIn(self.internal_group, r_user.groups.all())
        self.assertIn(new_group, r_user.groups.all())

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
        self.assertIn(self.internal_group, r_user.groups.all())
        self.assertIn(new_group, r_user.groups.all())

    def test_user_update(self):
        """Test user information update in middleware"""
        email1 = 'email1@email.com'
        email2 = 'email2@email.com'
        self.internal_user.email = email1
        self.internal_user.save()

        request = self.factory.get(self.url)
        request.META.update(**{
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
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
