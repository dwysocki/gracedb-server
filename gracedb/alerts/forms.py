from __future__ import absolute_import
from collections import defaultdict
import logging
import pyparsing
import textwrap

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.db.models import Q
from django.forms.utils import ErrorList
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.forms import MultipleForm
from events.models import Group, Search, Label
from .models import Notification, Contact
from .utils import parse_label_query

# Set up logger
logger =  logging.getLogger(__name__)


###############################################################################
# Notification forms ##########################################################
###############################################################################
class BaseNotificationForm(forms.ModelForm):
    """
    Base model for Notification forms. Should not be used on its own
    (essentially an abstract model)
    """
    class Meta:
        model = Notification
        fields = ['description'] # dummy placeholder
        labels = {
            'far_threshold': 'FAR Threshold (Hz)',
        }
        help_texts = {
            'contacts': ('If this box is empty, you must create and verify a '
                'contact.'),
            'label_query': textwrap.dedent("""\
                Label names can be combined with binary AND: ('&amp;' or ',')
                or binary OR: '|'. They can also be negated with '~' or '-'.
                For N labels, there must be exactly N-1 binary operators.
                Parentheses are not allowed.
            """).rstrip()
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(BaseNotificationForm, self).__init__(*args, **kwargs)

        # Dynamically set contacts queryset to be only contacts that:
        #  a) belong to the user
        #  b) are verified
        if user is not None:
            self.fields['contacts'].queryset = user.contact_set.filter(
                verified=True)

    def clean(self):
        cleaned_data = super(BaseNotificationForm, self).clean()

        # Dict for holding errors. Keys are class members,
        # values are lists of error messages
        err_dict = defaultdict(list)

        # Try to get fields from cleaned data
        label_query = cleaned_data.get('label_query', None)
        labels = cleaned_data.get('labels', None)

        # Can't specify a label from the list and a label query
        if label_query is not None and labels is not None:
            err_msg = ('Cannot specify both labels and label query, '
                'choose one or the other.')
            err_dict[NON_FIELD_ERRORS].append(err_msg)

        # If there is a label query, get the labels involved and store them
        # in the labels attribute.  We use this in the alert generation code
        # as an easy way of checking whether a notification might be triggered.
        if label_query is not None:
            try:
                labels = parse_label_query(label_query)
            except pyparsing.ParseException:
                err_dict['label_query'].append('Invalid label query.')
            else:
                cleaned_data['labels'] = Label.objects.filter(name__in=labels)

        # Raise errors, if any
        if err_dict:
            raise forms.ValidationError(err_dict)

        return cleaned_data


class SupereventNotificationForm(BaseNotificationForm, MultipleForm):
    key = 'superevent'
    category = Notification.NOTIFICATION_CATEGORY_SUPEREVENT

    class Meta(BaseNotificationForm.Meta):
        fields = ['description', 'contacts', 'far_threshold', 'labels',
            'label_query', 'ns_candidate', 'key_field']


class EventNotificationForm(BaseNotificationForm, MultipleForm):
    key = 'event'
    category = Notification.NOTIFICATION_CATEGORY_EVENT
    # Remove 'Test' group
    groups = forms.ModelMultipleChoiceField(queryset=
        Group.objects.exclude(name='Test'))
    # Remove 'MDC' and 'O2VirgoTest' searches
    searches = forms.ModelMultipleChoiceField(queryset=
        Search.objects.exclude(name__in=['MDC', 'O2VirgoTest']))

    class Meta(BaseNotificationForm.Meta):
        fields = ['description', 'contacts', 'far_threshold', 'groups',
            'pipelines', 'searches', 'labels', 'label_query', 'ns_candidate',
            'key_field']


###############################################################################
# Contact forms ###############################################################
###############################################################################
class PhoneContactForm(forms.ModelForm, MultipleForm):
    key = 'phone'

    class Meta:
        model = Contact
        fields = ['description', 'phone', 'phone_method', 'key_field']

    def __init__(self, *args, **kwargs):
        super(PhoneContactForm, self).__init__(*args, **kwargs)
        self.fields['phone_method'].required = True


class EmailContactForm(forms.ModelForm, MultipleForm):
    key = 'email'

    class Meta:
        model = Contact
        fields = ['description', 'email', 'key_field']


class VerifyContactForm(forms.ModelForm):
    code = forms.CharField(required=True, label='Verification code')

    class Meta:
        model = Contact
        fields = ['code']

    def clean(self):
        data = super(VerifyContactForm, self).clean()

        # Already verified
        if self.instance.verified:
            raise forms.ValidationError(_('This contact is already verified.'))

        if (self.instance.verification_code is None):
            raise forms.ValidationError(_('No verification code has been '
                'generated. Please request one before attempted to verify '
                'this contact.'))

        if (timezone.now() > self.instance.verification_expiration):
            raise forms.ValidationError(_('This verification code has '
                'expired. Please request a new one.'))

        return data

    def clean_code(self):
        code = self.cleaned_data['code']

        # Convert to an int
        try:
            code = int(code)
        except:
            raise forms.ValidationError(_('Incorrect verification code.'))

        if (code != self.instance.verification_code):
            raise forms.ValidationError(_('Incorrect verification code.'))

        return code
