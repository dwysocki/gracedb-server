import phonenumbers

from django.core.exceptions import ValidationError


def validate_phone(value):
    # Try to parse phone number
    try:
        phone = phonenumbers.parse(value, 'US')
    except phonenumbers.NumberParseException:
        raise ValidationError('Not a valid phone number: {0}'.format(value))

    # Validate phone number
    if not phonenumbers.is_valid_number(phone):
        raise ValidationError('Not a valid phone number: {0}'.format(value))
