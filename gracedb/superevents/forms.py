from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import Superevent, Log, Signoff
from .utils import create_log, create_signoff, update_signoff
from core.forms import ModelFormUpdateMixin
from core.vfile import VersionedFile

import os

import logging
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


class LogCreateForm(forms.ModelForm):
    # This field is used to get file upload, but is not actually
    # part of the Log model
    data_file = forms.FileField(label="Data file", required=False)

    class Meta:
        model = Log
        fields = ['issuer', 'superevent', 'filename', 'file_version',
            'data_file', 'comment']

    def __init__(self, *args, **kwargs):
        super(LogCreateForm, self).__init__(*args, **kwargs)

        # Make certain fields hidden in the web view. We will either specify
        # the value in the initial view or when we handle the POST data.
        self.fields['filename'].widget = forms.HiddenInput()
        self.fields['file_version'].widget = forms.HiddenInput()
        self.fields['issuer'].widget = forms.HiddenInput()
        self.fields['superevent'].widget = forms.HiddenInput()

    def save(self, commit=True):
        # Get data file (if present)
        create_log_args = self.cleaned_data.copy()
        create_log_args['issue_alert'] = True
        return create_log(**create_log_args)
