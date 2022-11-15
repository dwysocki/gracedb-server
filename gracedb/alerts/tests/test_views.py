try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import pytest

from django.conf import settings
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

        # Refresh from database to get formatted phone numbers
        cls.email_contact.refresh_from_db()
        cls.phone_contact.refresh_from_db()

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

        # Response = 302 means success and redirect to main alerts page
        self.assertEqual(response.status_code, 302)

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

        # Response = 302 means success and redirect to main alerts page
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        self.phone_contact.refresh_from_db()

        # Check values - description and method should be updated, but phone
        # number should not be
        self.assertEqual(self.phone_contact.description, data['description'])
        self.assertNotEqual(self.phone_contact.phone, data['phone'])
        self.assertEqual(self.phone_contact.phone, original_phone)
        self.assertEqual(self.phone_contact.phone_method, data['phone_method'])


@pytest.mark.skip(reason="Broke when upgrading django 2.2 -> 3.2, not sure why")
@pytest.mark.parametrize("notif_exists", [True, False])
@pytest.mark.django_db
def test_delete_contact(notif_exists, internal_user, client):
    client.force_login(internal_user)

    # Manually create verified contact for user
    contact = internal_user.contact_set.create(phone='12345678901',
        verified=True, phone_method=Contact.CONTACT_PHONE_TEXT,
        description='test')
    # Optionally create a notification
    if notif_exists:
        notif = internal_user.notification_set.create(description='test',
            category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)
        notif.contacts.add(contact)

    # Try to delete contact
    response = client.get(reverse('alerts:delete-contact', args=[contact.pk]))

    # Assert results
    if notif_exists:
        # Redirect to main alerts page
        assert response.status_code == 302
        assert response.url == reverse('alerts:index')
        # Message displayed by message framework
        assert "cannot be deleted" in response.cookies['messages'].value
        # Contact still exists
        assert Contact.objects.filter(pk=contact.pk).exists()
    else:
        # Redirect to main alerts page
        assert response.status_code == 302
        assert response.url == reverse('alerts:index')
        # Contact does not exist
        assert not Contact.objects.filter(pk=contact.pk).exists()


@pytest.mark.django_db
def test_create_notification_no_contact(internal_user, client):
    client.force_login(internal_user)

    # Manually create verified contact for user
    contact = internal_user.contact_set.create(phone='12345678901',
        verified=True, phone_method=Contact.CONTACT_PHONE_TEXT,
        description='test')

    # Try to create a notification with no contact
    url = reverse('alerts:create-notification')
    data = {
        'description': 'test',
        'key_field': 'superevent',
    }
    response = client.post(url, data=data)

    # This should call the forms_invalid() method of the CBV,
    # resulting in a TemplateResponse to render the form with
    # errors
    # Get form
    form = [form for form in response.context['forms']
        if form.key == 'superevent'][0]

    # Check form status and errors
    assert form.is_bound == True
    assert form.is_valid() == False
    assert 'contacts' in form.errors
    assert form.errors.as_data()['contacts'][0].code == 'required'


@mock.patch('alerts.models.twilio_client')
@mock.patch('alerts.models.get_twilio_from', lambda: '12345678901')
class TestRequestVerificationCode(GraceDbTestBase):
    def helper_test_verification_process(self, mock_twilio_client,
                                         **contact_kwargs):
        """Creates a Contact, requests and submits a verification code"""
        self.client.force_login(self.internal_user)

        # Create an unverified Contact
        contact = self.internal_user.contact_set.create(description='test',
                                                        **contact_kwargs)

        # Request the verification code
        url = reverse('alerts:request-verification-code', args=(contact.id,))
        response = self.client.get(url)

        # Redirect to verify contact page
        assert response.status_code == 302
        assert response.url == reverse('alerts:verify-contact', args=(contact.id,))

        # Update the Contact so the verification code is accessible
        contact.refresh_from_db()
        verification_code = contact.verification_code

        # Assert that the Contact is not yet verified
        assert not contact.verified

        # Submit the verification code
        url = reverse('alerts:verify-contact', args=(contact.id,))
        data = {
            'code': verification_code,
        }
        response = self.client.post(url, data=data)

        # Redirect to index
        assert response.status_code == 302
        assert response.url == reverse('alerts:index')

        # Assert that the Contact is now verified
        contact.refresh_from_db()
        assert contact.verified

    def test_verification_process_phone_call(self, mock_twilio_client):
        self.helper_test_verification_process(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_CALL, phone='12345678901')

    def test_verification_process_phone_text(self, mock_twilio_client):
        self.helper_test_verification_process(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_TEXT, phone='12345678901')

    def test_verification_process_phone_text(self, mock_twilio_client):
        self.helper_test_verification_process(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_BOTH, phone='12345678901')

    def test_verification_process_email(self, mock_twilio_client):
        self.helper_test_verification_process(mock_twilio_client,
            email='albert.einstein@ligo.org')

    def helper_test_contact_already_verified(self, mock_twilio_client,
                                             **contact_kwargs):
        """Tests that verification code not sent for verified Contact"""
        self.client.force_login(self.internal_user)

        # Create an unverified Contact
        contact = self.internal_user.contact_set.create(description='test',
            verified=True, **contact_kwargs)

        # Request the verification code
        url = reverse('alerts:request-verification-code', args=(contact.id,))
        response = self.client.get(url)

        # Redirect to index
        assert response.status_code == 302
        assert response.url == reverse('alerts:index')

        # No message should have been sent
        mock_twilio_client.assert_not_called()

    def test_contact_already_verified_phone_call(self, mock_twilio_client):
        self.helper_test_contact_already_verified(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_CALL, phone='12345678901')

    def test_contact_already_verified_phone_text(self, mock_twilio_client):
        self.helper_test_contact_already_verified(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_TEXT, phone='12345678901')

    def test_contact_already_verified_phone_both(self, mock_twilio_client):
        self.helper_test_contact_already_verified(mock_twilio_client,
            phone_method=Contact.CONTACT_PHONE_BOTH, phone='12345678901')

    def test_contact_already_verified_email(self, mock_twilio_client):
        self.helper_test_contact_already_verified(mock_twilio_client,
            email='albert.einstein@ligo.org')
