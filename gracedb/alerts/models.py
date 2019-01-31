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
from events.models import Label, Pipeline
from .fields import PhoneNumberField
from .phone import get_twilio_from


# Set up logger
logger = logging.getLogger(__name__)

# Set up user model
UserModel = get_user_model()


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
    description = models.CharField(max_length=20, blank=False, null=False)
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


class Notification(models.Model):
    user = models.ForeignKey(UserModel, null=False)
    labels = models.ManyToManyField(Label, blank=True)
    pipelines = models.ManyToManyField(Pipeline, blank=True)
    contacts = models.ManyToManyField(Contact, blank=False)
    far_threshold = models.FloatField(blank=True, null=True)
    label_query = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return (u"%s: %s") % (
            self.user.username,
            self.userlessDisplay()
        )

    def userlessDisplay(self):
        thresh = ""
        if self.far_threshold:
            thresh = " & (far < %s)" % self.far_threshold

        if self.label_query:
            label_disp = self.label_query
        else:
            label_disp = "|".join([a.name for a in self.labels.all()]) or "creating"

        return ("(%s) & (%s)%s -> %s") % (
            "|".join([a.name for a in self.pipelines.all()]) or "any pipeline",
            label_disp,
            thresh,
            ", ".join([x.description for x in self.contacts.all()])
        )
