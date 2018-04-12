from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import Superevent, Log
from .utils import create_log
from core.forms import ModelFormUpdateMixin
from core.vfile import VersionedFile
from events.models import Event

import os

import logging
logger = logging.getLogger(__name__)


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
        #return create_log(**self.cleaned_data, issue_alert=True)
        #data_file = self.cleaned_data.pop('data_file', None)

        ## Inherited save from ModelForm
        #obj = super(LogCreateForm, self).save(commit)

        ## Do other stuff with data file
        #if data_file:
        #    filepath = os.path.join(obj.superevent.datadir,
        #        self.cleaned_data['filename'])
        #    fdest = VersionedFile(filepath, 'w')
        #    for chunk in data_file.chunks():
        #        fdest.write(chunk)
        #    fdest.close()

        #    obj.file_version = fdest.version
        #    if commit:
        #        obj.save()

        #return obj
