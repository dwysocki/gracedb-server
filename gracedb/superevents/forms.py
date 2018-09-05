import logging
import os

from django import forms

from superevents.models import Signoff

# Set up logger
logger = logging.getLogger(__name__)


class SignoffForm(forms.ModelForm):

    class Meta:
        model = Signoff
        fields = ['status', 'comment', 'signoff_type', 'instrument']

    def __init__(self, *args, **kwargs):
        super(SignoffForm, self).__init__(*args, **kwargs)
        # Hide some fields that we will populate either by default
        # when we instantiate the form or with the request data
        self.fields['signoff_type'].widget = forms.HiddenInput()
        self.fields['instrument'].widget = forms.HiddenInput()
