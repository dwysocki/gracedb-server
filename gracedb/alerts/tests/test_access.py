import mock

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.urls import reverse

from core.tests.utils import GraceDbTestBase
from alerts.models import Contact, Notification


class TestIndexView(GraceDbTestBase):
    """Test user access to main userprofile index page"""

    def test_internal_user_get(self):
        """Internal user can get to index view"""
        url = reverse('userprofile-home')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can get to index view"""
        url = reverse('userprofile-home')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_public_user_get(self):
        """Public user can get to index view"""
        url = reverse('userprofile-home')
        response = self.request_as_user(url, "GET")
        # Should be redirected to login page
        self.assertEqual(response.status_code, 302)


class TestManagePasswordView(GraceDbTestBase):
    """Test user access to page for generating basic auth password for API"""

    def test_internal_user_get(self):
        """Internal user *can't* get to manage password page"""
        url = reverse('userprofile-manage-password')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 403)

    def test_lvem_user_get(self):
        """LV-EM user can get to manage password page"""
        url = reverse('userprofile-manage-password')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 200)

    def test_public_user_get(self):
        """Public user can't get to manage password page"""
        url = reverse('userprofile-manage-password')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


class TestContactCreationView(GraceDbTestBase):
    """Test user access to contact creation view"""

    def test_internal_user_get(self):
        """Internal user can get contact creation view"""
        url = reverse('userprofile-create-contact')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can't get contact creation view"""
        url = reverse('userprofile-create-contact')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get contact creation view"""
        url = reverse('userprofile-create-contact')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


# Prevent test emails from going out
@mock.patch('userprofile.views.EmailMessage')
class TestContactTestView(GraceDbTestBase):
    """Test user access to contact testing view"""

    @classmethod
    def setUpTestData(cls):
        super(TestContactTestView, cls).setUpTestData()

        # Create a contact
        cls.contact = Contact.objects.create(user=cls.internal_user,
            desc='test contact', email='test@test.com')

    def test_internal_user_test(self, mock_email_message):
        """Internal user can test contacts"""
        url = reverse('userprofile-test-contact', args=[self.contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to userprofile index page
        # after the test
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('userprofile-home'))

    def test_lvem_user_test(self, mock_email_message):
        """LV-EM user can't test contacts"""
        url = reverse('userprofile-create-contact')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_test(self, mock_email_message):
        """Public user can't test contacts"""
        url = reverse('userprofile-create-contact')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


class TestContactDeleteView(GraceDbTestBase):
    """Test user access to contact deletion view"""

    @classmethod
    def setUpTestData(cls):
        super(TestContactDeleteView, cls).setUpTestData()

        # Create a contact
        cls.contact = Contact.objects.create(user=cls.internal_user,
            desc='test contact', email='test@test.com')

        # Create another contact
        cls.other_contact = Contact.objects.create(user=cls.lvem_user,
            desc='test contact', email='test@test.com')

    def test_internal_user_delete(self):
        """Internal user can delete their contacts"""
        url = reverse('userprofile-delete-contact', args=[self.contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to userprofile index page
        # after the contact is deleted
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('userprofile-home'))
        # Assert that contact is deleted
        with self.assertRaises(self.contact.DoesNotExist):
            self.contact.refresh_from_db()

    def test_internal_user_delete_other(self):
        """Internal user can't delete other users' contacts"""
        url = reverse('userprofile-delete-contact',
            args=[self.other_contact.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You are not authorized to modify another user's Contacts.")

    def test_lvem_user_get(self):
        """LV-EM user can't delete contacts"""
        # Even if an LV-EM user somehow ended up with a contact
        # (see self.other_contact), they can't delete it.
        for c in Contact.objects.all():
            url = reverse('userprofile-delete-contact', args=[c.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't delete contacts"""
        for c in Contact.objects.all():
            url = reverse('userprofile-delete-contact', args=[c.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)


class TestNotificationCreateView(GraceDbTestBase):
    """Test user access to notification creation view"""

    def test_internal_user_get(self):
        """Internal user can get notification creation view"""
        url = reverse('userprofile-create')
        response = self.request_as_user(url, "GET", self.internal_user)
        self.assertEqual(response.status_code, 200)

    def test_lvem_user_get(self):
        """LV-EM user can't get notification creation view"""
        url = reverse('userprofile-create')
        response = self.request_as_user(url, "GET", self.lvem_user)
        self.assertEqual(response.status_code, 403)

    def test_public_user_get(self):
        """Public user can't get notification creation view"""
        url = reverse('userprofile-create')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)


class TestNotificationDeleteView(GraceDbTestBase):
    """Test user access to notification deletion view"""

    @classmethod
    def setUpTestData(cls):
        super(TestNotificationDeleteView, cls).setUpTestData()

        # Create a contact and a notification
        cls.contact = Contact.objects.create(user=cls.internal_user,
            desc='test contact', email='test@test.com')
        cls.notification = Notification.objects.create(user=cls.internal_user)
        cls.notification.contacts.add(cls.contact)

        # Create another contact and notification
        cls.other_contact = Contact.objects.create(user=cls.lvem_user,
            desc='test contact', email='test@test.com')
        cls.other_notification = Notification.objects.create(user=cls.lvem_user)
        cls.other_notification.contacts.add(cls.other_contact)

    def test_internal_user_delete(self):
        """Internal user can delete their notifications"""
        url = reverse('userprofile-delete', args=[self.notification.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to userprofile index page
        # after the notification is deleted
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('userprofile-home'))
        # Assert that contact is deleted
        with self.assertRaises(self.notification.DoesNotExist):
            self.notification.refresh_from_db()

    def test_internal_user_delete_other(self):
        """Internal user can't delete other users' notifications"""
        url = reverse('userprofile-delete', args=[self.other_notification.id])
        response = self.request_as_user(url, "GET", self.internal_user)
        # Expect 302 since we are redirected to userprofile index page
        # after the notification is deleted
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content,
            "You are not allowed to modify another user's notifications.")

    def test_lvem_user_delete(self):
        """LV-EM user can't delete notifications"""
        for t in Notification.objects.all():
            url = reverse('userprofile-delete', args=[t.id])
            response = self.request_as_user(url, "GET", self.lvem_user)
            self.assertEqual(response.status_code, 403)

    def test_public_user_delete(self):
        """Public user can't get delete notifications"""
        for t in Notification.objects.all():
            url = reverse('userprofile-delete', args=[t.id])
            response = self.request_as_user(url, "GET")
            self.assertEqual(response.status_code, 403)
        url = reverse('userprofile-create')
        response = self.request_as_user(url, "GET")
        self.assertEqual(response.status_code, 403)
