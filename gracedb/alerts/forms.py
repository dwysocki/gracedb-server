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
from .fields import ContactMultipleChoiceField
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
    contacts = ContactMultipleChoiceField(queryset=Contact.objects.all(),
        required=False, widget=forms.widgets.SelectMultiple(attrs={'size': 6}))
    class Meta:
        model = Notification
        fields = ['description'] # dummy placeholder
        labels = {
            'far_threshold': 'FAR Threshold (Hz)',
            'ns_candidate': 'Neutron star candidate',
        }
        help_texts = {
            'contacts': textwrap.dedent("""\
                Select a contact or contacts to receive the notification.
                If this box is empty, you must create and verify a contact.
            """).rstrip(),
            'far_threshold': textwrap.dedent("""\
                Require that the candidate has FAR less than this threshold.
                Leave blank to place no requirement on FAR.
            """).rstrip(),
            'labels': textwrap.dedent("""\
                Require that a label or labels must be attached to the
                candidate. You can specify labels here or in the label query,
                but not both.
            """).rstrip(),
            'label_query': textwrap.dedent("""\
                Require that the candidate's set of labels matches this query.
                Label names can be combined with binary AND: ('&amp;' or ',')
                or binary OR: '|'. They can also be negated with '~' or '-'.
                For N labels, there must be exactly N-1 binary operators.
                Parentheses are not allowed.
            """).rstrip(),
            'ns_candidate': ('Require that the candidate has m<sub>2</sub> '
                '< 3.0 M<sub>sun</sub>.'),
        }
        widgets = {
            'far_threshold': forms.widgets.TextInput(),
            'labels': forms.widgets.SelectMultiple(attrs={'size': 8}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(BaseNotificationForm, self).__init__(*args, **kwargs)

        # We need a user for this to work
        assert user is not None
        assert user.is_authenticated

        # Dynamically set contacts queryset to be only contacts that:
        #  a) belong to the user
        #  b) are verified
        if user is not None:
            self.fields['contacts'].queryset = user.contact_set.filter(
                verified=True)

        # Sort the queryset for labels by name
        self.fields['labels'].queryset = \
            self.fields['labels'].queryset.order_by('name')

    def clean(self):
        cleaned_data = super(BaseNotificationForm, self).clean()

        # Dict for holding errors. Keys are class members,
        # values are lists of error messages
        err_dict = defaultdict(list)

        # Try to get fields from cleaned data
        label_query = cleaned_data.get('label_query', None)
        labels = cleaned_data.get('labels', None)

        # Can't specify a label from the list and a label query
        # No label specified in the form looks like an empty queryset here
        if label_query is not None and (labels is not None and labels.exists()):
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

    def clean_far_threshold(self):
        far_threshold = self.cleaned_data['far_threshold']

        # If it's set, make sure it's positive
        if far_threshold is not None:
            # We can assume it's a float due to previous
            # validation/cleaning
            if (far_threshold <= 0):
                raise forms.ValidationError(
                    'FAR threshold must be a positive number.')

        return far_threshold


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
        Group.objects.exclude(name='Test').order_by('name'), required=False,
        help_text=("Require that the analysis group for the candidate is "
        "this group or in this set of groups. Leave blank to place no "
        "requirement on group."))
    # Remove 'MDC' and 'O2VirgoTest' searches
    searches = forms.ModelMultipleChoiceField(queryset=
        Search.objects.exclude(name__in=['MDC', 'O2VirgoTest']).order_by('name'),
        required=False, widget=forms.widgets.SelectMultiple(attrs={'size': 6}),
        help_text=("Require that the analysis search for the candidate is "
        "this search or in this set of searches. Leave blank to place no "
        "requirement on search."))

    class Meta(BaseNotificationForm.Meta):
        fields = ['description', 'contacts', 'far_threshold', 'groups',
            'pipelines', 'searches', 'labels', 'label_query', 'ns_candidate',
            'key_field']
        help_texts = BaseNotificationForm.Meta.help_texts
        help_texts.update({'pipelines': textwrap.dedent("""\
            Require that the analysis pipeline for the candidate is this
            pipeline or in this set of pipelines. Leave blank to place no
            requirement on pipeline.
            """).rstrip()
        })
        widgets = BaseNotificationForm.Meta.widgets
        widgets.update({
            'pipelines': forms.widgets.SelectMultiple(attrs={'size': 6}),
        })

    def __init__(self, *args, **kwargs):
        super(EventNotificationForm, self).__init__(*args, **kwargs)

        # Sort the queryset for pipelines by name
        self.fields['pipelines'].queryset = \
            self.fields['pipelines'].queryset.order_by('name')


###############################################################################
# Contact forms ###############################################################
###############################################################################
class PhoneContactForm(forms.ModelForm, MultipleForm):
    key = 'phone'

    class Meta:
        model = Contact
        fields = ['description', 'phone', 'phone_method', 'key_field']
        labels = {
            'phone': 'Phone number',
        }
        help_texts = {
            'phone': ('Non-US numbers should include the country code, '
                'including the preceding \'+\'.'),
        }

    def __init__(self, *args, **kwargs):
        super(PhoneContactForm, self).__init__(*args, **kwargs)
        self.fields['phone_method'].required = True


class EmailContactForm(forms.ModelForm, MultipleForm):
    key = 'email'

    class Meta:
        model = Contact
        fields = ['description', 'email', 'key_field']
        labels = {
            'email': 'Email address',
        }


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
