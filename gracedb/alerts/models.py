from collections import defaultdict
import logging
import random
import textwrap

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.mail import EmailMessage
from django.db import models
from django.utils import timezone
from django.utils.http import urlencode

from django_twilio.client import twilio_client

from core.models import CleanSaveModel
from .fields import PhoneNumberField
from .phone import get_twilio_from


# Set up logger
logger = logging.getLogger(__name__)

# Set up user model
UserModel = get_user_model()

###############################################################################
# Contacts ####################################################################
###############################################################################
class Contact(CleanSaveModel):
    # Phone contact methods
    CONTACT_PHONE_CALL = 'C'
    CONTACT_PHONE_TEXT = 'T'
    CONTACT_PHONE_BOTH = 'B'
    CONTACT_PHONE_METHODS = (
        (CONTACT_PHONE_CALL, 'Call'),
        (CONTACT_PHONE_TEXT, 'Text'),
        (CONTACT_PHONE_BOTH, 'Call and text'),
    )
    # Number of digits in verification codes
    CODE_DIGITS = 6

    # Fields
    user = models.ForeignKey(UserModel, null=False)
    description = models.CharField(max_length=30, blank=False, null=False)
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(blank=True, max_length=255, null=True)
    phone_method = models.CharField(max_length=1, null=True, blank=True,
        choices=CONTACT_PHONE_METHODS, default=None)
    verified = models.BooleanField(default=False, editable=False)
    verification_code = models.IntegerField(null=True, editable=False)
    verification_expiration = models.DateTimeField(null=True, editable=False)


    def __unicode__(self):
        return u"{0}: {1}".format(self.user.username, self.description)

    def clean(self):
        # Mostly used for preventing creation of bad Contact
        # objects through the Django interface.
        super(Contact, self).clean()

        err_dict = defaultdict(list)
        # If a phone number is given, require either call or text to be True.
        if (self.phone is not None and self.phone_method is None):
            err_msg = 'Choose a phone contact method.'
            err_dict['phone_method'].append(err_msg)

        if (self.phone is None and self.phone_method is not None):
            err_msg = '"Call" and "text" should be False for non-phone alerts.'
            err_dict['phone'].append(err_msg)

        # Only one contact method is allowed
        if (self.email is not None and self.phone is not None):
            err_msg = \
                'Only one contact method (email or phone) can be selected.'
            err_dict[NON_FIELD_ERRORS].append(err_msg)

        # If no e-mail or phone given, raise error.
        # We have to skip this due to really annoying behavior with forms.. :(
        #if not (self.email or self.phone):
        #    err_msg = \
        #        'One contact method (email or phone) is required.'
        #    err_dict[NON_FIELD_ERRORS].append(err_msg)

        if err_dict:
            raise ValidationError(err_dict)

    def generate_verification_code(self):
        self.verification_code = random.randint(10**(self.CODE_DIGITS-1),
            (10**self.CODE_DIGITS)-1)
        self.verification_expiration = timezone.now() + \
            settings.VERIFICATION_CODE_LIFETIME
        self.save(update_fields=['verification_code',
            'verification_expiration'])

    def send_verification_code(self):
        # Message for texts and emails
        msg = ('Verification code for contact "{desc}" on {host}: {code}. '
            'If you did not request a verification code or do not know what '
            'this is, please disregard.').format(desc=self.description,
            host=settings.LIGO_FQDN, code=self.verification_code)

        if self.email:
            subject = 'Verification code for contact "{desc}" on {host}' \
                .format(desc=self.description, host=settings.LIGO_FQDN)
            email = EmailMessage(subject, msg,
                from_email=settings.ALERT_EMAIL_FROM, to=[self.email])
            email.send()
        elif self.phone:
            from_ = get_twilio_from()

            if (self.phone_method == self.CONTACT_PHONE_CALL):
                # If phone method is only call, send a call

                # Convert code to a string with spaces between the numbers
                # so it's pronounced properly by text-to-voice
                code = " ".join(str(self.verification_code))
                urlparams = urlencode({'code': code})
                twiml_url = '{base}{twiml_bin}?{params}'.format(
                    base=settings.TWIML_BASE_URL,
                    twiml_bin=settings.TWIML_BIN['verify'],
                    params=urlparams)
                twilio_client.calls.create(to=self.phone, from_=from_,
                    url=twiml_url, method='GET')
            else:
                # If method is text or both, send a text
                twilio_client.messages.create(to=self.phone, from_=from_,
                    body=msg)

    def verify(self):
        self.verified = True
        self.save(update_fields=['verified'])

    def display(self):
        if self.email:
            return "Email {0}".format(self.email)
        elif self.phone:
            if self.phone_method == self.CONTACT_PHONE_BOTH:
                return "Call and text {0}".format(self.phone)
            elif self.phone_method == self.CONTACT_PHONE_CALL:
                return "Call {0}".format(self.phone)
            if self.phone_method == self.CONTACT_PHONE_TEXT:
                return "Text {0}".format(self.phone)

    def print_info(self):
        """Prints information about Contact object; useful for debugging."""
        info_str = textwrap.dedent("""\
            Contact "{description}" (user {username})
            E-mail: {email}
            Phone: {phone} (method={method})
            Verified: {verified}
        """).format(description=self.description, username=self.user.username,
        email=self.email, phone=self.phone, method=self.phone_method,
        verified=self.verified)
        print(info_str)


###############################################################################
# Notifications ###############################################################
###############################################################################
class Notification(models.Model):
    # Notification categories
    NOTIFICATION_CATEGORY_EVENT = 'E'
    NOTIFICATION_CATEGORY_SUPEREVENT = 'S'
    NOTIFICATION_CATEGORY_CHOICES = (
        (NOTIFICATION_CATEGORY_EVENT, 'Event'),
        (NOTIFICATION_CATEGORY_SUPEREVENT, 'Superevent'),
    )
    user = models.ForeignKey(UserModel, null=False)
    contacts = models.ManyToManyField(Contact)
    description = models.CharField(max_length=40, blank=False, null=False)
    far_threshold = models.FloatField(blank=True, null=True)
    labels = models.ManyToManyField('events.label', blank=True)
    label_query = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=1, null=False, blank=False,
        choices=NOTIFICATION_CATEGORY_CHOICES,
        default=NOTIFICATION_CATEGORY_SUPEREVENT)
    # Whether the event possibly has a neutron star in it.
    # The logic for determining this is defined in a method below.
    ns_candidate = models.BooleanField(default=False)
    # Event-only fields
    groups = models.ManyToManyField('events.group', blank=True)
    pipelines = models.ManyToManyField('events.pipeline', blank=True)
    searches = models.ManyToManyField('events.search', blank=True)

    def __unicode__(self):
        return (u"%s: %s") % (
            self.user.username,
            self.display()
        )

    def display(self):
        kwargs = {}
        if self.category == self.NOTIFICATION_CATEGORY_EVENT:
            output = 'Event'
        elif self.category == self.NOTIFICATION_CATEGORY_SUPEREVENT:
            output = 'Superevent'

        # Add label stuff
        if self.label_query or self.labels.exists():
            action = 'labeled with {labels}'
            if self.label_query:
                labels = '({0})'.format(self.label_query)
            else:
                labels = " | ".join([l.name for l in self.labels.all()])
                if self.labels.count() > 1:
                    labels = '({0})'.format(labels)
            action = action.format(labels=labels)
        else:
            action = 'created or updated'
        output += ' {action}'.format(action=action)

        # Add groups, pipelines, searches for event-type notifications
        if self.category == self.NOTIFICATION_CATEGORY_EVENT:
            output += ' & {groups} & {pipelines} & {searches}'
            if self.groups.exists():
                kwargs['groups'] = 'group=({0})'.format(
                    " | ".join([g.name for g in self.groups.all()]))
            else:
                kwargs['groups'] = 'any group'
            if self.pipelines.exists():
                kwargs['pipelines'] = 'pipeline=({0})'.format(
                    " | ".join([p.name for p in self.pipelines.all()]))
            else:
                kwargs['pipelines'] = 'any pipeline'
            if self.searches.exists():
                kwargs['searches'] = 'search=({0})'.format(
                    " | ".join([s.name for s in self.searches.all()]))
            else:
                kwargs['searches'] = 'any search'

        # Optionally add FAR threshold
        if self.far_threshold:
            output += ' & (FAR < {far_threshold})'
            kwargs['far_threshold'] = self.far_threshold

        # Optionally add NS candidate info
        if self.ns_candidate:
            output += ' & NS candidate'

        # Add contacts
        output += ' -> {contacts}'
        kwargs['contacts'] = \
            ", ".join([c.description for c in self.contacts.all()])

        return output.format(**kwargs)
