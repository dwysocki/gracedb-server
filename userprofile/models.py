
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
        validators = kwargs.get('validators', []) + [validate_phone]
        kwargs = dict(kwargs, max_length=255, validators=validators)
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
    phone = PhoneNumberField(blank=True)

    def __unicode__(self):
        #return "%s: %s" % (self.user.name, self.desc)
        return u"{0} {1}: {2}".format(self.user.first_name, self.user.last_name, self.desc)

    # Require at least one contact method (e-mail or phone).
    def clean(self):
        if not self.email and not self.phone:
            raise ValidationError('At least one contact method (email, phone) is required')

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

