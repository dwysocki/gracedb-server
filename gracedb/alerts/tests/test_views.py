import mock

from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.urls import reverse

from core.tests.utils import GraceDbTestBase
from alerts.models import Contact, Notification



class TestUpdateContactView(GraceDbTestBase):

    @classmethod
    def setUpTestData(cls):
        super(TestUpdateContactView, cls).setUpTestData()

        # Create email and phone contacts
        cls.email_contact = Contact.objects.create(user=cls.internal_user,
            description='test email', email='test@test.com')
        cls.phone_contact = Contact.objects.create(user=cls.internal_user,
            description='test phone', phone='12345678901',
            phone_method=Contact.CONTACT_PHONE_BOTH)

    def test_edit_email(self):
        """Users should not be able to update contact email"""
        # (because it sidesteps the verification process)
        data = {
            'key_field': 'email',
            'description': 'new description',
            'email': 'new@new.com',
        }
        original_email = self.email_contact.email
        url = reverse('alerts:edit-contact', args=[self.email_contact.pk])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=data)

        # Refresh from database
        self.email_contact.refresh_from_db()

        # Check values - description should be updated, but email should not be
        self.assertEqual(self.email_contact.description, data['description'])
        self.assertNotEqual(self.email_contact.email, data['email'])
        self.assertEqual(self.email_contact.email, original_email)


    def test_edit_phone(self):
        """Users should not be able to update contact phone"""
        # (because it sidesteps the verification process)
        data = {
            'key_field': 'phone',
            'description': 'new description',
            'phone': '23456789012',
            'phone_method': Contact.CONTACT_PHONE_CALL,
        }
        original_phone = self.phone_contact.phone
        url = reverse('alerts:edit-contact', args=[self.phone_contact.pk])
        response = self.request_as_user(url, "POST", self.internal_user,
            data=data)

        # Refresh from database
        self.phone_contact.refresh_from_db()

        # Check values - description and method should be updated, but phone
        # number should not be
        self.assertEqual(self.phone_contact.description, data['description'])
        self.assertNotEqual(self.phone_contact.phone, data['phone'])
        self.assertEqual(self.phone_contact.phone, original_phone)
        self.assertEqual(self.phone_contact.phone_method, data['phone_method'])
