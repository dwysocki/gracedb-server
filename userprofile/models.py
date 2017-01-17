
from django.db import models

from gracedb.models import Label, Pipeline

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import phonenumbers

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
        return u"{0} {1}: {2}".format(self.user.first_name,
            self.user.last_name, self.desc)

    def clean(self):
        # Mostly used for preventing creation of bad Contact
        # objects through the Django interface.
        super(Contact, self).clean()

        # If a phone number is given, require either call or text to be True.
        if self.phone and not (self.call_phone or self.text_phone):
            raise ValidationError({'phone':
                'Choose "call" or "text" (or both) for phone alerts.'})

        if not self.phone and (self.call_phone or self.text_phone):
            raise ValidationError({'phone':
                '"Call" and "text" should be False for non-phone alerts.'})

        # If no e-mail or phone given, raise error.
        if not (self.email or self.phone):
            raise ValidationError(('At least one contact method'
                                  ' (email, phone) is required.'))

    # Override save method by requiring fully_cleaned objects.
    def save(self):
        self.full_clean()
        super(Contact, self).save()

    def print_info(self):
        """Prints information about Contact object; useful for debugging."""
        print('Contact "{0}" (user {1}):'.format(self.desc,self.user.username))
        print('\tE-mail: {0}'.format(self.email))
        print('\tPhone: {0} (call={1}, text={2})'.format(self.phone,
                self.call_phone, self.text_phone))

class Trigger(models.Model):
    TYPES = ( ("create", "create"), ("change","change"), ("label","label") )
    user = models.ForeignKey(User, null=False)
    #new_user = models.ForeignKey(DjangoUser, null=True)
    triggerType = models.CharField(max_length=20, choices=TYPES, blank=True)
    labels = models.ManyToManyField(Label, blank=True)
    #atypes = models.ManyToManyField(AnalysisType, blank=True, verbose_name="Analysis Types")
    pipelines = models.ManyToManyField(Pipeline, blank=True)
    contacts = models.ManyToManyField(Contact, blank=True)
    farThresh = models.FloatField(blank=True, null=True)
    label_query = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        return (u"%s %s: %s") % (
            self.user.first_name,
            self.user.last_name,
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

