import logging
import os
import shutil

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from guardian.conf import settings as guardian_settings
from guardian.models import GroupObjectPermission, UserObjectPermission

from events.models import Tag
from ligoauth.models import AuthGroup

# Set up user model
UserModel = get_user_model()

# Directory for testing data
TEST_DATA_DIR = os.path.join('/tmp', 'test_data')


@override_settings(
    SEND_XMPP_ALERTS=False,
    SEND_PHONE_ALERTS=False,
    SEND_EMAIL_ALERTS=False,
    GRACEDB_DATA_DIR=TEST_DATA_DIR,
)
class DefineTestSettings(TestCase):
    """
    Defines base settings for testing and creates a data directory.

    NOTE: we technically should be checking for and creating/deleting
    settings.GRACEDB_DATA_DIR since we are overriding it.  But we use
    TEST_DATA_DIR instead just to be totally safe and not accidentally
    delete all of the real data.
    """

    def setUp(self):
        super(DefineTestSettings, self).setUp()
        # Create a temporary data dir
        if not os.path.isdir(TEST_DATA_DIR):
            os.mkdir(TEST_DATA_DIR)

    def tearDown(self):
        super(DefineTestSettings, self).tearDown()
        # Remove the temporary data dir
        if os.path.isdir(TEST_DATA_DIR):
            shutil.rmtree(TEST_DATA_DIR)


class InternalGroupAndUserSetup(TestCase):
    """
    Base class which sets up internal (LVC) group and adds a user to it.
    These are accessible with self.internal_group and self.internal_user.
    Also adds appropriate permissions.
    """
    @classmethod
    def setUpTestData(cls):

        # Run super
        super(InternalGroupAndUserSetup, cls).setUpTestData()

        # Get or create internal group
        cls.internal_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVC_GROUP)
        if created:
            cls.internal_group.ldap_name = 'internal_ldap_group'
            cls.internal_group.save(update_fields=['ldap_name'])

        # Get or create user
        cls.internal_user, _ = UserModel.objects.get_or_create(
            username='internal.user')

        # Add user to groups
        cls.internal_group.user_set.add(cls.internal_user)

        # Get permissions
        superevent_permissions_codenames = [
            'add_labelling',
            'delete_labelling',
            'tag_log',
            'untag_log',
            'view_log',
            'add_test_superevent',
            'change_test_superevent',
            'confirm_gw_test_superevent',
            'annotate_superevent',
            'view_superevent',
            'add_voevent',
            'view_supereventgroupobjectpermission',
            'view_signoff',
        ]
        perms = Permission.objects.filter(
            content_type__app_label='superevents',
            codename__in=superevent_permissions_codenames)
        cls.internal_group.permissions.add(*perms)


class LvemGroupAndUserSetup(TestCase):
    """
    Base class which sets up LV-EM group, LV-EM observers group, and adds a
    user to them. These are accessible with self.lvem_group,
    self.lvem_obs_group, and self.lvem_user.
    """
    @classmethod
    def setUpTestData(cls):
        # Run super
        super(LvemGroupAndUserSetup, cls).setUpTestData()

        # Get or create LV-EM group
        cls.lvem_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVEM_GROUP)
        if created:
            cls.lvem_group.ldap_name = 'lvem_ldap_group'
            cls.lvem_group.save(update_fields=['ldap_name'])

        # Get or create LV-EM observers group
        lvem_obs_tag, _ = Tag.objects.get_or_create(name='lvem')
        cls.lvem_obs_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVEM_OBSERVERS_GROUP)
        if created:
            cls.lvem_obs_group.ldap_name = 'lvem_observers_ldap_group'
            cls.lvem_obs_group.tag = lvem_obs_tag
            cls.lvem_obs_group.save(update_fields=['ldap_name', 'tag'])

        # Get or create user
        cls.lvem_user, _ = UserModel.objects.get_or_create(
            username='lvem.user')

        # Add user to groups
        cls.lvem_group.user_set.add(cls.lvem_user)
        cls.lvem_obs_group.user_set.add(cls.lvem_user)


class SupereventManagersGroupAndUserSetup(TestCase):
    """
    Base class which sets up superevent_managers group and user
    These are accessible with self.sm_group and self.sm_user.
    Also adds appropriate permissions.
    """
    @classmethod
    def setUpTestData(cls):

        # Run super
        super(SupereventManagersGroupAndUserSetup, cls).setUpTestData()

        # Get or create superevent managers
        cls.sm_group, _ = AuthGroup.objects.get_or_create(
            name='superevent_managers')

        # Get or create user
        cls.sm_user, _ = UserModel.objects.get_or_create(
            username='superevent.manager')

        # Add user to superevent managers group
        cls.sm_group.user_set.add(cls.sm_user)

        # Also add user to internal group
        internal_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVC_GROUP)
        if created:
            internal_group.ldap_name = 'internal_ldap_group'
            internal_group.save(update_fields=['ldap_name'])
        internal_group.user_set.add(cls.sm_user)

        # Get permissions
        sm_permissions_codenames = [
            'add_mdc_superevent',
            'add_superevent',
            'add_test_superevent',
            'change_mdc_superevent',
            'change_superevent',
            'change_test_superevent',
            'confirm_gw_mdc_superevent',
            'confirm_gw_superevent',
            'confirm_gw_test_superevent',
        ]
        perms = Permission.objects.filter(
            content_type__app_label='superevents',
            codename__in=sm_permissions_codenames)
        cls.sm_group.permissions.add(*perms)


class AccessManagersGroupAndUserSetup(TestCase):
    """
    Base class which sets up access_managers group and user
    These are accessible with self.am_group and self.am_user.
    Also adds appropriate permissions.
    """
    @classmethod
    def setUpTestData(cls):

        # Run super
        super(AccessManagersGroupAndUserSetup, cls).setUpTestData()

        # Get or create access managers
        cls.am_group, _ = AuthGroup.objects.get_or_create(
            name='access_managers')

        # Get or create user
        cls.am_user, _ = UserModel.objects.get_or_create(
            username='access.manager')

        # Add user to access managers group
        cls.am_group.user_set.add(cls.am_user)

        # Also add user to internal group
        internal_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVC_GROUP)
        if created:
            internal_group.ldap_name = 'internal_ldap_group'
            internal_group.save(update_fields=['ldap_name'])
        internal_group.user_set.add(cls.am_user)

        # Get permissions
        am_permissions_codenames = [
            'expose_superevent',
            'hide_superevent',
            'expose_log',
            'hide_log',
        ]
        perms = Permission.objects.filter(
            content_type__app_label='superevents',
            codename__in=am_permissions_codenames)
        cls.am_group.permissions.add(*perms)


class SignoffGroupsAndUsersSetup(TestCase):
    """
    Base class which sets up signoff groups ([ifo]_control_room and
    em_advocates) and groups for each one. Users are accessible under
    self.[ifo]_user and self.adv_user.

    Also adds appropriate permissions.
    """
    @classmethod
    def setUpTestData(cls):

        # Run super
        super(SignoffGroupsAndUsersSetup, cls).setUpTestData()

        # Internal group, used later
        internal_group, created = AuthGroup.objects.get_or_create(
            name=settings.LVC_GROUP)
        if created:
            internal_group.ldap_name = 'internal_ldap_group'
            internal_group.save(update_fields=['ldap_name'])

        # Get or create IFO control room groups and users, and add perms
        ifos = ['H1', 'L1', 'V1']
        for ifo in ifos:
            # Create groups and usres
            g, _ = AuthGroup.objects.get_or_create(
                name=(ifo + '_control_room'))
            user, _ = UserModel.objects.get_or_create(username=(ifo + '.user'))
            user.groups.add(g)
            setattr(cls, ifo + '_user', user)

            # Also add user to internal group
            internal_group.user_set.add(user)

            # Add permission
            p = Permission.objects.filter(
                content_type__app_label='superevents',
                codename=('do_' + ifo + '_signoff'))
            g.permissions.add(*p)

        # Same for em advocates
        g, created = AuthGroup.objects.get_or_create(name='em_advocates')
        if created:
            g.ldap_name = 'em_advocates_ldap_group'
            g.save(update_fields=['ldap_name'])
        user, _ = UserModel.objects.get_or_create(username='em.advocate')
        user.groups.add(g)
        cls.adv_user = user

        p = Permission.objects.filter(
            content_type__app_label='superevents',
            codename='do_adv_signoff')
        g.permissions.add(*p)
        p = Permission.objects.filter(
            content_type__app_label='events',
            codename='manage_pipeline')
        g.permissions.add(*p)
        # Also add user to internal group
        internal_group.user_set.add(user)

        # Add add/change/delete perms to all of these groups
        ctrl_room_groups = [ifo + '_control_room' for ifo in ifos]
        grps = ctrl_room_groups + ['em_advocates']
        permission_codenames = [
            'add_signoff',
            'change_signoff',
            'delete_signoff',
        ]
        for grp_name in grps:
            group = AuthGroup.objects.get(name=grp_name)
            perms = Permission.objects.filter(
                content_type__app_label='superevents',
                codename__in=permission_codenames)
            group.permissions.add(*perms)


class PublicGroupSetup(TestCase):
    """
    Base class which creates a public group and the guardian AnonymousUser,
    and puts that user in the public group.
    """

    @classmethod
    def setUpTestData(cls):
        # Run super
        super(PublicGroupSetup, cls).setUpTestData()

        # Get or create public group
        public_tag, _ = Tag.objects.get_or_create(name='public')
        cls.public_group, created = AuthGroup.objects.get_or_create(
            name=settings.PUBLIC_GROUP)
        if created:
            cls.public_group.tag = public_tag
            cls.public_group.save(update_fields=['tag'])

        # Create guardian AnonymousUser and add to group
        anonymous_user, _ = UserModel.objects.get_or_create(username=
            guardian_settings.ANONYMOUS_USER_NAME)
        cls.public_group.user_set.add(anonymous_user)


class GraceDbTestBase(DefineTestSettings, InternalGroupAndUserSetup,
    LvemGroupAndUserSetup, PublicGroupSetup):
    """
    Combines all test base classes and defines method for easily making
    requests with a specfic user account.

    Also disables logging.
    """

    @classmethod
    def setUpClass(cls):
        super(GraceDbTestBase, cls).setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        super(GraceDbTestBase, cls).tearDownClass()
        logging.disable(logging.NOTSET)

    def request_as_user(self, url, method, user=None, data=None, **extra):
        """Shortcut function for making a request"""
        # Get client method for HTTP method requested
        try:
            method_func = getattr(self.client, method.lower())
        except Exception as e:
            raise ValueError('{method} is not a valid HTTP method'.format(
                method=method))

        # If we have a user account
        if user:
            # We use force_login because it's faster and the details of the
            # login process aren't relevant.  We will explicitly test that
            # process in a set of unit tests.
            self.client.force_login(user)

        # Make request
        response = method_func(url, data=data, **extra)

        # Log user out, otherwise session persists throughout the current unit
        # test.  This could lead to mistakes, so we are playing it safe here.
        if user:
            self.client.logout()

        # Return response
        return response
