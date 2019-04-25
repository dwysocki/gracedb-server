try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.urls import reverse

from core.tests.utils import GraceDbTestBase
from alerts.models import Contact, Notification


class TestIndexView(GraceDbTestBase):
    """Test user access to main alerts index page"""

    def test_internal_user_get(self):
        """Internal user can get to index view"""
        url = reverse('alerts:index')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can get to index view"""
        url = reverse('alerts:index')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get to index view"""
        url = reverse('alerts:index')
        response = self.request_as_user(url, "GET")
        # Should be redirected to login page
        self.assertEqual(response.status_code, 403)


class TestContactCreationView(GraceDbTestBase):
    """Test user access to contact creation view"""

    def test_internal_user_get(self):
        """Internal user can get contact creation view"""
        url = reverse('alerts:create-contact')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can't get contact creation view"""
        url = reverse('alerts:create-contact')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get contact creation view"""
        url = reverse('alerts:create-contact')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


# Prevent test emails from going out
@mock.patch('alerts.views.EmailMessage')
class TestContactTestView(GraceDbTestBase):
    """Test user access to contact testing view"""

    @classmethod
    def setUpTestData(cls):
        super(TestContactTestView, cls).setUpTestData()

        # Create a contact
        cls.contact = Contact.objects.create(user=cls.internal_user,
            description='test contact', email='test@test.com')

    def test_internal_user_test(self, mock_email_message):
        """Internal user can test contacts"""
        url = reverse('alerts:test-contact', args=[self.contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to alerts index page
        # after the test
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('alerts:index'))

    def test_lvem_user_test(self, mock_email_message):
        """LV-EM user can't test contacts"""
        url = reverse('alerts:create-contact')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_test(self, mock_email_message):
        """Public user can't test contacts"""
        url = reverse('alerts:create-contact')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


class TestContactDeleteView(GraceDbTestBase):
    """Test user access to contact deletion view"""

    @classmethod
    def setUpTestData(cls):
        super(TestContactDeleteView, cls).setUpTestData()

        # Create a contact
        cls.contact = Contact.objects.create(user=cls.internal_user,
            description='test contact', email='test@test.com')

        # Create another contact
        cls.other_contact = Contact.objects.create(user=cls.lvem_user,
            description='test contact', email='test@test.com')

    def test_internal_user_delete(self):
        """Internal user can delete their contacts"""
        url = reverse('alerts:delete-contact', args=[self.contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to alerts index page
        # after the contact is deleted
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('alerts:index'))
        # Assert that contact is deleted
        with self.assertRaises(self.contact.DoesNotExist):
            self.contact.refresh_from_db()

    def test_internal_user_delete_other(self):
        """Internal user can't delete other users' contacts"""
        url = reverse('alerts:delete-contact',
            args=[self.other_contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_get(self):
        """LV-EM user can't delete contacts"""
        # Even if an LV-EM user somehow ended up with a contact
        # (see self.other_contact), they can't delete it.
        for c in Contact.objects.all():
            url = reverse('alerts:delete-contact', args=[c.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't delete contacts"""
        for c in Contact.objects.all():
            url = reverse('alerts:delete-contact', args=[c.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)


class TestNotificationCreateView(GraceDbTestBase):
    """Test user access to notification creation view"""

    def test_internal_user_get_with_verified_contact(self):
        """
        Internal user can get notification creation view if they have a
        verified contact
        """
        url = reverse('alerts:create-notification')
        self.internal_user.contact_set.create(phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_TEXT, verified=True,
            description='test')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_internal_user_get_with_no_verified_contact(self):
        """
        Internal user can't get notification creation view if they don't have
        a verified contact
        """
        url = reverse('alerts:create-notification')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('alerts:index'))

    def test_lvem_user_get(self):
        """LV-EM user can't get notification creation view"""
        url = reverse('alerts:create-notification')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get notification creation view"""
        url = reverse('alerts:create-notification')
        response = self.request_as_user(url, "GET")
        # User should be redirected to login view
        self.assertEqual(response.status_code, 403)


class TestNotificationDeleteView(GraceDbTestBase):
    """Test user access to notification deletion view"""

    @classmethod
    def setUpTestData(cls):
        super(TestNotificationDeleteView, cls).setUpTestData()

        # Create a contact and a notification
        cls.contact = Contact.objects.create(user=cls.internal_user,
            description='test contact', email='test@test.com')
        cls.notification = Notification.objects.create(user=cls.internal_user)
        cls.notification.contacts.add(cls.contact)

        # Create another contact and notification
        # We use lvem_user as the user account just so it can be used for
        # testing deletion of another user's contacts. But in reality, an
        # LV-EM user should never have a contact or notification
        cls.other_contact = Contact.objects.create(user=cls.lvem_user,
            description='test contact', email='test@test.com')
        cls.other_notification = Notification.objects.create(
            user=cls.lvem_user)
        cls.other_notification.contacts.add(cls.other_contact)

    def test_internal_user_delete(self):
        """Internal user can delete their notifications"""
        url = reverse('alerts:delete-notification',
            args=[self.notification.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to alerts index page
        # after the notification is deleted
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('alerts:index'))
        # Assert that contact is deleted
        with self.assertRaises(self.notification.DoesNotExist):
            self.notification.refresh_from_db()

    def test_internal_user_delete_other(self):
        """Internal user can't delete other users' notifications"""
        url = reverse('alerts:delete-notification',
            args=[self.other_notification.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 404)

    def test_lvem_user_delete(self):
        """LV-EM user can't delete notifications"""
        for t in Notification.objects.all():
            url = reverse('alerts:delete-notification', args=[t.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_public_user_delete(self):
        """Public user can't delete notifications"""
        for t in Notification.objects.all():
            url = reverse('alerts:delete-notification', args=[t.id])
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)
