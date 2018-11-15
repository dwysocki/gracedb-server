from django.conf import settings
from django.test import RequestFactory
from django.test.utils import override_settings, modify_settings
from django.contrib.auth.models import Group, User, AnonymousUser
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sessions.middleware import SessionMiddleware

from ligoauth.middleware import ShibbolethWebAuthMiddleware

# See this test class for information about what groups and users
# are already defined for use.
from core.tests.utils import GraceDbTestBase

class TestX509Authentication(GraceDbTestBase):
    """
    """

    @classmethod
    def setUpClass(cls):
        # Make sure middleware is installed
        if not any(['GraceDbX509Authentication' in m for m in
           settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']]):
            raise ImproperlyConfigured(('GraceDbX509Authentication must be '
                'installed in the DEFAULT_AUTHENTICATION_CLASSES element '
                'of the REST_FRAMEWORK dictionary in your project settings'))

        # Attach request factory to class
        cls.factory = RequestFactory()

        # Attach middleware to class
        #cls.middleware = ShibbolethWebAuthMiddleware()

    @classmethod
    def setUpTestData(cls):
        # Call base class setUpTestData
        super(TestX509Authentication, cls).setUpTestData()

    @classmethod
    def setUp(cls):
        cls.request = cls.factory.get(reverse('home'))
        cls.request.user = AnonymousUser()
        SessionMiddleware().process_request(cls.request)
        cls.request.session.save()

    def test_web_path(self):
        pass

    def test_basic_api_path(self):
        pass

    def test_internal_user_auth(self):
        # Can we check backend with this type of setup?
        pass

    def test_lvem_user_auth(self):
        pass

    def test_public_user_auth(self):
        pass

    def test_proxy_auth(self):
        # test proxy pattern thing
        pass

#class TestBasicAuthentication(GraceDbTestBase):
# Make sure to test password expiration

class TestShibbolethWebAuthMiddleware(GraceDbTestBase):

    @classmethod
    def setUpClass(cls):
        # Make sure middleware is installed
        if not any(['ShibbolethWebAuthMiddleware' in m for m in
           settings.MIDDLEWARE]):
            raise ImproperlyConfigured(
                'ShibbolethWebAuthMiddleware must be installed in MIDDLEWARE')

        # Attach request factory to class
        cls.factory = RequestFactory()

        # Attach middleware to class
        cls.middleware = ShibbolethWebAuthMiddleware()

    @classmethod
    def setUpTestData(cls):
        # Call base class setUpTestData
        super(TestShibbolethWebAuthMiddleware, cls).setUpTestData()

    @classmethod
    def setUp(cls):
        cls.request = cls.factory.get(reverse('home'))
        cls.request.user = AnonymousUser()
        SessionMiddleware().process_request(cls.request)
        cls.request.session.save()

    def test_internal_authentication(self):
        """Test internal user authentication"""
        self.request.META = {
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
        }
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertIn(self.internal_group, self.request.user.groups.all())

    def test_lvem_authentication(self):
        """Test lvem user authentication"""
        self.request.META = {
            settings.SHIB_USER_HEADER: self.lvem_user.username,
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.name,
        }
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the lvem group is
        # attached to the user account and that the internal group
        # is NOT attached to the user account
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertIn(self.lvem_obs_group, self.request.user.groups.all())
        self.assertNotIn(self.internal_group, self.request.user.groups.all())

    def test_public_authentication(self):
        """Test middleware on public user"""
        self.middleware.process_request(self.request)

        # Make sure user is not authenticated and is anonymous,
        # auth backend is not set, and the user has no groups
        self.assertFalse(self.request.user.is_authenticated)
        self.assertTrue(self.request.user.is_anonymous)
        self.assertFalse(hasattr(self.request.user, 'backend'))
        self.assertTrue(self.request.user.groups.count() == 0)

    def test_internal_user_creation(self):
        """Test creating a new internal user in the auth framework"""
        new_user_dict = {
            'username': 'new_internal.user',
            'email': 'new_internal.user@group.org',
        }
        self.request.META = {
            settings.SHIB_USER_HEADER: new_user_dict['username'],
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
            settings.SHIB_ATTRIBUTE_MAP['email']: new_user_dict['email'],
        }
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertIn(self.internal_group, new_user.groups.all())
        self.assertEqual(new_user.username, new_user_dict['username'])
        self.assertEqual(new_user.email, new_user_dict['email'])

    def test_lvem_user_creation(self):
        """Test creating a new lvem user in the auth framework"""
        new_user_dict = {
            'username': 'new_lvem.user',
            'email': 'new_lvem.user@group.org',
        }
        self.request.META = {
            settings.SHIB_USER_HEADER: new_user_dict['username'],
            settings.SHIB_GROUPS_HEADER: self.lvem_obs_group.name,
            settings.SHIB_ATTRIBUTE_MAP['email']: new_user_dict['email'],
        }
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')

        # Make sure user information is correct
        new_user = User.objects.get(username=new_user_dict['username'])
        self.assertIn(self.lvem_obs_group, new_user.groups.all())
        self.assertEqual(new_user.username, new_user_dict['username'])
        self.assertEqual(new_user.email, new_user_dict['email'])

    def test_group_addition(self):
        """Test group addition in middleware"""
        # Create new group for testing
        new_group = Group.objects.create(name='new_group')

        delim = ShibbolethWebAuthMiddleware.group_delimiter
        groups_str = delim.join([self.internal_group.name, new_group.name])
        self.request.META = {
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: groups_str,
        }

        # Make sure user just has internal group initially
        self.assertTrue(self.internal_user.groups.count() == 1)
        self.assertTrue(self.internal_user.groups.all()[0] == 
            self.internal_group)

        # Process request
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the two groups attached are what
        # we expect
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertTrue(self.internal_user.groups.count() == 2)
        self.assertIn(self.internal_group, self.internal_user.groups.all())
        self.assertIn(new_group, self.internal_user.groups.all())

    def test_group_removal(self):
        """Test group addition in middleware"""
        # Create new group, add to user
        new_group = Group.objects.create(name='new_group')
        self.internal_user.groups.add(new_group)

        # Shib session doesn't have new_group in it
        self.request.META = {
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
        }

        # Make sure user just has internal group initially
        self.assertTrue(self.internal_user.groups.count() == 2)
        self.assertIn(self.internal_group, self.internal_user.groups.all())
        self.assertIn(new_group, self.internal_user.groups.all())

        # Process request
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and only the internal group is attached
        # to the user
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')
        self.assertTrue(self.internal_user.groups.count() == 1)
        self.assertTrue(self.internal_user.groups.all()[0] == 
            self.internal_group)
        self.assertNotIn(new_group, self.internal_user.groups.all())

    def test_user_update(self):
        """Test user information update in middleware"""
        email1 = 'email1@email.com'
        email2 = 'email2@email.com'
        self.internal_user.email = email1
        self.internal_user.save()

        self.request.META = {
            settings.SHIB_USER_HEADER: self.internal_user.username,
            settings.SHIB_GROUPS_HEADER: self.internal_group.name,
            settings.SHIB_ATTRIBUTE_MAP['email']: email2,
        }

        # Check email just to be sure
        self.assertEqual(email1, self.internal_user.email)

        # Process request
        self.middleware.process_request(self.request)

        # Make sure user is authenticated and was authenticated by
        # the shibboleth backend and that the internal group is
        # attached to the user account
        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.backend,
            'ligoauth.backends.ShibbolethRemoteUserBackend')

        # Make sure email is changed as expected
        self.internal_user.refresh_from_db()
        self.assertEqual(email2, self.internal_user.email)

    def test_webapi(self):
        pass
