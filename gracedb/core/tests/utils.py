import os
import shutil

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from guardian.models import GroupObjectPermission, UserObjectPermission

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
    """Defines base settings for testing and creates a data directory"""

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
        cls.internal_group, _ = Group.objects.get_or_create(
            name=settings.LVC_GROUP)

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
    Base class which sets up LV-EM group and adds a user to it.
    These are accessible with self.lvem_group and self.lvem_user.
    """
    @classmethod
    def setUpTestData(cls):
        # Run super
        super(LvemGroupAndUserSetup, cls).setUpTestData()

        # Get or create LV-EM observers group
        cls.lvem_group, _ = Group.objects.get_or_create(
            name=settings.LVEM_OBSERVERS_GROUP)

        # Get or create user
        cls.lvem_user, _ = UserModel.objects.get_or_create(
            username='lvem.user')

        # Add user to group
        cls.lvem_group.user_set.add(cls.lvem_user)


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
        cls.sm_group, _ = Group.objects.get_or_create(
            name='superevent_managers')

        # Get or create user
        cls.sm_user, _ = UserModel.objects.get_or_create(
            username='superevent.manager')

        # Add user to superevent managers group
        cls.sm_group.user_set.add(cls.sm_user)

        # Also add user to internal group
        internal_group, _ = Group.objects.get_or_create(
            name=settings.LVC_GROUP)
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
        cls.am_group, _ = Group.objects.get_or_create(
            name='access_managers')

        # Get or create user
        cls.am_user, _ = UserModel.objects.get_or_create(
            username='access.manager')

        # Add user to access managers group
        cls.am_group.user_set.add(cls.am_user)

        # Also add user to internal group
        internal_group, _ = Group.objects.get_or_create(
            name=settings.LVC_GROUP)
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
        internal_group, _ = Group.objects.get_or_create(
            name=settings.LVC_GROUP)

        # Get or create IFO control room groups and users, and add perms
        ifos = ['H1', 'L1', 'V1']
        for ifo in ifos:
            # Create groups and usres
            g, _ = Group.objects.get_or_create(name=(ifo + '_control_room'))
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
        g, _ = Group.objects.get_or_create(name='em_advocates')
        user, _ = UserModel.objects.get_or_create(username='em.advocate')
        user.groups.add(g)
        cls.adv_user = user

        p = Permission.objects.filter(
            content_type__app_label='superevents',
            codename='do_adv_signoff')
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
            group = Group.objects.get(name=grp_name)
            perms = Permission.objects.filter(
                content_type__app_label='superevents',
                codename__in=permission_codenames)
            group.permissions.add(*perms)


class PublicGroupSetup(TestCase):
    """Base class which creates a public group"""

    @classmethod
    def setUpTestData(cls):
        # Run super
        super(PublicGroupSetup, cls).setUpTestData()

        # Get or create public group
        cls.public_group, _ = Group.objects.get_or_create(
            name=settings.PUBLIC_GROUP)


class GraceDbTestBase(DefineTestSettings, InternalGroupAndUserSetup,
    LvemGroupAndUserSetup, PublicGroupSetup):
    """
    Combines all test base classes and defines method for easily making
    requests with a specfic user account.
    """

    def request_as_user(self, url, method, user=None, data=None, **kwargs):
        """Shortcut function for making a request"""
        # Get client method for HTTP method requested
        try:
            method_func = getattr(self.client, method.lower())
        except Exception as e:
            raise ValueError('{method} is not a valid HTTP method'.format(
                method=method))

        if user is not None:
            # Set up user dict
            user_dict = {
                'HTTP_REMOTE_USER': user.username,
                'HTTP_ISMEMBEROF': ';'.join([g.name for g in
                    user.groups.all()]),
            }
            if kwargs:
                user_dict.update(**kwargs)

            # Make request and return response
            return method_func(url, data, **user_dict)
        else:
            # Anonymous user
            return method_func(url, data)

