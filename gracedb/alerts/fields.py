from django.db import models

from .validators import validate_phone


class PhoneNumberField(models.CharField):
    validators = [validate_phone]
