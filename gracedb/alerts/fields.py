import phonenumbers

from django.db import models

from .validators import validate_phone


PHONE_NUMBER_FORMATS = ['E164', 'NATIONAL', 'INTERNATIONAL', 'RFC3966']


class PhoneNumberField(models.CharField):
    validators = [validate_phone]

    def __init__(self, *args, **kwargs):
        # Get format and check values
        self.format = kwargs.pop('format', 'E164')
        if self.format not in PHONE_NUMBER_FORMATS:
            raise ValueError('Phone number format must be one of {fmt}'.format(
                fmt=", ".join(PHONE_NUMBER_FORMATS)))

        # super __init__
        super(PhoneNumberField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super(PhoneNumberField, self).get_prep_value(value)

        # Handle blank values
        if value is None or value == '':
            return value

        # Return phone number as a formatted string
        phone = phonenumbers.parse(value, 'US')
        return phonenumbers.format_number(phone,
            getattr(phonenumbers.PhoneNumberFormat, self.format))
