import logging

from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape
from .models import Event, Group, Label
from .models import Pipeline, Search, Signoff
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.forms import ModelForm

from pyparsing import ParseException

# Set up logger
logger = logging.getLogger(__name__)


class CreateEventForm(forms.Form):
    eventFile = forms.FileField()
    group = forms.ModelChoiceField(queryset=Group.objects.all(), to_field_name='name')
    pipeline = forms.ModelChoiceField(queryset=Pipeline.objects.all(), to_field_name='name')
    search = forms.ModelChoiceField(queryset=Search.objects.all(), to_field_name='name',
        required=False)
    # List of labels as a comma-separated string
    labels = forms.ModelMultipleChoiceField(queryset=Label.objects.all(),
        required=False, to_field_name='name')

    # Offline boolean. required=False means that if the user
    # doesn't provide a value, we use the default defined in models.py.
    # This ensures backwards-compatibility for client versions which
    # don't specify this parameter.
    offline = forms.BooleanField(required=False)

    def clean(self):
        cleaned_data = super(CreateEventForm, self).clean()

        # Don't allow protected labels
        labels = cleaned_data.get('labels')
        protected_labels = labels.filter(protected=True)
        if protected_labels.exists():
            raise forms.ValidationError({'labels': 'The following label(s) are'
                ' managed automatically and cannot be manually applied: {0}'
                .format(', '.join([l.name for l in protected_labels]))})

        return cleaned_data


class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = [ 'status', 'comment' ] 
