import pytest

from django.contrib.auth import get_user_model

from alerts.models import Contact, Notification
from alerts.recipients import CreationRecipientGetter

UserModel = get_user_model()


@pytest.mark.django_db
def test_multiple_contacts(superevent, internal_user):
    # Set up contacts and notifications
    c1 = Contact.objects.create(
        user=internal_user, description='c1', verified=True,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    c2 = Contact.objects.create(
        user=internal_user, description='c2', verified=True,
        email='test@test.com'
    )
    n = Notification.objects.create(
        user=internal_user, description='test',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n.contacts.add(*(c1, c2))

    # Get recipients 
    recipient_getter = CreationRecipientGetter(superevent)
    email_contacts, phone_contacts = recipient_getter.get_recipients()

    # Check results
    assert email_contacts.count() == 1
    assert email_contacts.first().pk == c2.pk
    assert phone_contacts.count() == 1
    assert phone_contacts.first().pk == c1.pk


@pytest.mark.django_db
def test_duplicate_contacts(superevent, internal_user):
    # Set up contacts and notifications
    c = Contact.objects.create(
        user=internal_user, description='test', verified=True,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    n1 = Notification.objects.create(
        user=internal_user, description='n1',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n2 = Notification.objects.create(
        user=internal_user, description='n2',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n1.contacts.add(c)
    n2.contacts.add(c)

    # Get notifications and check results
    recipient_getter = CreationRecipientGetter(superevent)
    notifications = recipient_getter.get_notifications()
    assert notifications.count() == 2
    for pk in (n1.pk, n2.pk):
        assert notifications.filter(pk=pk).exists()
   
    # Get recipients and check results 
    email_contacts, phone_contacts = recipient_getter.get_recipients()

    # Check results
    assert email_contacts.count() == 0
    assert phone_contacts.count() == 1
    assert phone_contacts.first().pk == c.pk


@pytest.mark.django_db
def test_contacts_non_internal_user(superevent, internal_user):
    # NOTE: this test handles the case where a user with contacts/notifications
    # already set up leaves the collboration.

    # Create a non-internal user
    external_user = UserModel.objects.create(username='external.user')

    # Set up contacts and notifications
    c_internal = Contact.objects.create(
        user=internal_user, description='test', verified=True,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    c_external = Contact.objects.create(
        user=external_user, description='test', verified=True,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    n_internal = Notification.objects.create(
        user=internal_user, description='internal',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n_internal.contacts.add(c_internal)
    n_external = Notification.objects.create(
        user=external_user, description='external',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n_external.contacts.add(c_external)

    # Get notifications and check results
    recipient_getter = CreationRecipientGetter(superevent)
    notifications = recipient_getter.get_notifications()
    assert notifications.count() == 2
    for pk in (n_internal.pk, n_external.pk):
        assert notifications.filter(pk=pk).exists()
   
    # Get recipients and check results 
    email_contacts, phone_contacts = recipient_getter.get_recipients()

    # Check results
    assert email_contacts.count() == 0
    assert phone_contacts.count() == 1
    assert phone_contacts.first().pk == c_internal.pk


@pytest.mark.django_db
def test_unverified_contact(superevent, internal_user):
    # NOTE: this test handles the case where a user with contacts/notifications
    # already set up leaves the collboration.

    # Set up contacts and notifications
    c_verified = Contact.objects.create(
        user=internal_user, description='test', verified=True,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    c_unverified = Contact.objects.create(
        user=internal_user, description='test', verified=False,
        phone='12345678901', phone_method=Contact.CONTACT_PHONE_TEXT,
    )
    n = Notification.objects.create(
        user=internal_user, description='internal',
        category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT
    )
    n.contacts.add(*(c_verified, c_unverified))

    # Get notifications and check results
    recipient_getter = CreationRecipientGetter(superevent)
    notifications = recipient_getter.get_notifications()
    assert notifications.count() == 1
    assert notifications.first().pk == n.pk
   
    # Get recipients and check results 
    email_contacts, phone_contacts = recipient_getter.get_recipients()

    # Check results
    assert email_contacts.count() == 0
    assert phone_contacts.count() == 1
    assert phone_contacts.first().pk == c_verified.pk
