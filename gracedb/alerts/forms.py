from collections import defaultdict
import logging
from pyparsing import ParseException

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.forms import MultipleForm
from search.query.labels import parseLabelQuery
from .models import Notification, Contact

# Set up logger
logger =  logging.getLogger(__name__)


class CleanNotificationFormMixin(object):

    def clean(self):
        data = super(CleanNotificationFormMixin, self).clean()
        return data

    def clean_label_query(self):
        label_query = self.cleaned_data['label_query']
        return label_query


class SupereventNotificationForm(forms.ModelForm, MultipleForm,
    CleanNotificationFormMixin):
    key = 'superevent'
    category = Notification.NOTIFICATION_CATEGORY_SUPEREVENT

    class Meta:
        model = Notification
        fields = ['description', 'contacts', 'far_threshold', 'labels',
            'label_query', 'ns_candidate', 'key_field']


class EventNotificationForm(forms.ModelForm, MultipleForm,
    CleanNotificationFormMixin):
    key = 'event'
    category = Notification.NOTIFICATION_CATEGORY_EVENT

    class Meta:
        model = Notification
        fields = ['description', 'contacts', 'far_threshold', 'groups',
            'pipelines', 'searches', 'labels', 'label_query', 'ns_candidate',
            'key_field']


def notificationFormFactory(postdata=None, user=None):
    class TF(forms.ModelForm):
        far_threshold = forms.FloatField(label='FAR Threshold (Hz)',
            required=False)
        class Meta:
            model = Notification
            fields = ['contacts', 'pipelines', 'far_threshold', 'labels', 'label_query']
            widgets = {'label_query': forms.TextInput(attrs={'size': 50})} 

            help_texts = {
                'label_query': ("Label names can be combined with binary AND: "
                                "'&amp;' or ','; or binary OR: '|'. For N "
                                "labels, there must be exactly N-1 binary "
                                "operators. Parentheses are not allowed. "
                                "Additionally, any of the labels in a query "
                                "string can be negated with '~' or '-'. "
                                "Labels can either be selected with the select"
                                " box at the top, or a query can be specified,"
                                " <i>but not both</i>."),
            }

        contacts = forms.ModelMultipleChoiceField(
                        queryset=Contact.objects.filter(user=user),
                        required=True,
                        help_text="If this box is empty, go back and create a contact first.",
                        error_messages={'required': 'You must specify at least one contact.'})
    
        # XXX should probably override is_valid and check for
        # truth of (atypes or labels)
        # and set field error attributes appropriately.

        def clean(self, *args, **kwargs):
            cleaned_data = super(TF, self).clean(*args, **kwargs)

            # Dict for holding errors. Keys are class members,
            # values are lists of error messages
            err_dict = defaultdict(list)

            # Can't specify a label from the list and a label query
            if (cleaned_data['label_query'] and cleaned_data['labels']):
                err_msg = ('Cannot specify both labels and label query, '
                    'choose one or the other.')
                err_dict[NON_FIELD_ERRORS].append(err_msg)

            # Notifications currently require a label or a pipeline to be
            # specified. In the future, we should also allow the cases which
            # have only a FAR threshold or a label query
            if not (cleaned_data['labels'] or cleaned_data['pipelines']):
                err_msg = ('Choose labels and/or pipelines for this '
                    'notification.')
                err_dict[NON_FIELD_ERRORS].append(err_msg)

            # Make sure the label query is valid
            if cleaned_data['label_query']:
                # now try parsing it
                try:
                    parseLabelQuery(cleaned_data['label_query'])
                except ParseException:
                    err_dict['label_query'].append('Invalid label query')

            # Raise errors, if any
            if err_dict:
                raise forms.ValidationError(err_dict)

            return cleaned_data

        def as_table(self, *args, **kwargs):
            """
            Overriding default as_table method to put non-field errors
            at the top of the table. Allows removal of "flash message box".
            """

            # Get non-field errors and remove them from the error list
            # to prevent duplicates.
            nfe = self.non_field_errors()
            self.errors[NON_FIELD_ERRORS] = []

            # Generate table HTML and add non-field errors to beginning row
            table_data = super(TF, self).as_table(*args, **kwargs)
            if nfe:
                table_data = '\n<tr><td colspan="2">\n' + \
                    process_errors(nfe) + '\n</td></tr>\n' + table_data
            return mark_safe(table_data)

    if postdata is not None:
        return TF(postdata)
    else:
        return TF()

def process_errors(err):
    """Processes and formats errors in ContactForms."""
    out_errs = []
    if isinstance(err,ErrorList):
        for e in err:
            out_errs.append('<p class="error">{0}</p>' \
                .format(conditional_escape(e)))
    elif isinstance(err,str):
        out_errs.append('<p class="error">{0}</p>' \
                .format(conditional_escape(err)))
    else:
        out_errs.append(force_text(err))

    return "\n".join(out_errs)


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
