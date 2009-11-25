from django import forms
from django.db import models
from models import Trigger, Contact

from django.forms.models import modelformset_factory

class TriggerForm(forms.ModelForm):
    class Meta:
        model = Trigger
        exclude = ['user', 'triggerType']


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        exclude = ['user']

