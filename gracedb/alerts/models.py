from django.db import models
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.contrib.auth.models import User

from events.models import Label, Pipeline

from collections import defaultdict
import phonenumbers
import logging
log = logging.getLogger(__name__)

def validate_phone(value):
    try:
        phone = phonenumbers.parse(value, 'US')
    except phonenumbers.NumberParseException:
        raise ValidationError('Not a valid phone number: {0}'.format(value))
    if not phonenumbers.is_valid_number(phone):
        raise ValidationError('Not a valid phone number: {0}'.format(value))
    return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

class PhoneNumberField(models.CharField):

    def __init__(self, *args, **kwargs):
        super(PhoneNumberField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value:
            return validate_phone(value)
        else:
            return ''

#class Notification(models.Model):
#    user = models.ForeignKey(User, null=False)
#    onLabel = models.ManyToManyField(Label, blank=True)
#    onTypeCreate = models.CharField(max_length=20, choices=TYPES, blank=True)
#    onTypeChange = models.CharField(max_length=20, choices=TYPES, blank=True)
#    email = models.EmailField()

class Contact(models.Model):
    user = models.ForeignKey(User, null=False)
    #new_user = models.ForeignKey(DjangoUser, null=True)
    desc = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    phone = PhoneNumberField(blank=True, max_length=255,
                             validators=[validate_phone])
    # These fields specify whether alert should be a phone
    # call or text (or both).
    call_phone = models.BooleanField(default=False)
    text_phone = models.BooleanField(default=False)

    def __unicode__(self):
        return u"{0}: {1}".format(self.user.username, self.desc)

    def clean(self):
        # Mostly used for preventing creation of bad Contact
        # objects through the Django interface.
        super(Contact, self).clean()

        err_dict = defaultdict(list)
        # If a phone number is given, require either call or text to be True.
        if self.phone and not (self.call_phone or self.text_phone):
            err_msg = 'Choose "call" or "text" (or both) for phone alerts.'
            err_dict['phone'].append(err_msg)

        if not self.phone and (self.call_phone or self.text_phone):
            err_msg = '"Call" and "text" should be False for non-phone alerts.'
            err_dict['phone'].append(err_msg)

        # If no e-mail or phone given, raise error.
        if not (self.email or self.phone):
            err_msg = 'At least one contact method (email, phone) is required.'
            err_dict[NON_FIELD_ERRORS].append(err_msg)

        if err_dict:
            raise ValidationError(err_dict)

    # Override save method by requiring fully_cleaned objects.
    def save(self, *args, **kwargs):
        self.full_clean()
        super(Contact, self).save()

    def print_info(self):
        """Prints information about Contact object; useful for debugging."""
        print('Contact "{0}" (user {1}):'.format(self.desc,self.user.username))
        print('\tE-mail: {0}'.format(self.email))
        print('\tPhone: {0} (call={1}, text={2})'.format(self.phone,
                self.call_phone, self.text_phone))

class Trigger(models.Model):
    # TP 6 Jul 2017: TYPES and triggerType don't seem to be used anywhere...
    TYPES = ( ("create", "create"), ("change","change"), ("label","label") )
    triggerType = models.CharField(max_length=20, choices=TYPES, blank=True)

    user = models.ForeignKey(User, null=False)
    labels = models.ManyToManyField(Label, blank=True)
    pipelines = models.ManyToManyField(Pipeline, blank=True)
    contacts = models.ManyToManyField(Contact, blank=False)
    farThresh = models.FloatField(blank=True, null=True)
    label_query = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return (u"%s: %s") % (
            self.user.username,
            self.userlessDisplay()
        )

    def userlessDisplay(self):
        thresh = ""
        if self.farThresh:
            thresh = " & (far < %s)" % self.farThresh

        if self.label_query:
            label_disp = self.label_query
        else:
            label_disp = "|".join([a.name for a in self.labels.all()]) or "creating"

        return ("(%s) & (%s)%s -> %s") % (
            "|".join([a.name for a in self.pipelines.all()]) or "any pipeline",
            label_disp,
            thresh,
            ", ".join([x.desc for x in self.contacts.all()])
        )

