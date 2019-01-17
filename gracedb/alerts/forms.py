from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.forms.utils import ErrorList
from django.core.exceptions import NON_FIELD_ERRORS

from .models import Notification, Contact
from search.query.labels import parseLabelQuery

from pyparsing import ParseException
from collections import defaultdict
import logging
log = logging.getLogger(__name__)

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

class ContactForm(forms.ModelForm):
    # Adjust labels.
    desc = forms.CharField(label='Description', required=True)
    call_phone = forms.BooleanField(label='Call', initial=False,
                                    required=False)
    text_phone = forms.BooleanField(label='Text', initial=False,
                                    required=False)

    class Meta:
        model = Contact
        fields = ['desc','email','phone','call_phone','text_phone']
        help_texts = {
            'phone': 'Prototype service: may not be available in the future.'
        }

    # Custom generator for table format.
    def as_table(self):
        row_head = '<tr><th><label for="id_{0}">{1}:</label></th>'
        row_err = '<td>{2}'
        row_input = '<input id="id_{0}" name="{0}" type="{3}" /></td></tr>'
        row_str = row_head + row_err + row_input
        table_data = {}

        # Build table -----------------------------
        # Description/email
        for field in ['desc','email']:
            table_data[field] = row_str.format(field,self[field].label,
                process_errors(self[field].errors),"text")

        # Phone number
        table_data['phone'] = (row_head + row_err +
            '<input id="id_{0}" name="{0}" type="text" />').format(
            'phone',self['phone'].label,process_errors(self['phone'].errors))
        # Add call/text checkboxes.
        table_data['phone'] += '<br />'
        table_data['phone'] += ('{1}?<input id="id_{0}" name="{0}"'
            'type="checkbox" />&nbsp;&nbsp;'.format('call_phone',
            self['call_phone'].label))
        table_data['phone'] += ('{1}?<input id="id_{0}" name="{0}"'
            'type="checkbox" />'.format('text_phone',self['text_phone'].label))

        # Add phone help text.
        table_data['phone'] += ('<br /><span class="helptext">{0}</span>'
            '</td></tr>\n'.format(self['phone'].help_text))

        # Compile table_data dict into a list.
        td = [table_data[k] for k in ['desc','email','phone']]

        # Add non-field errors to beginning.
        nfe = self.non_field_errors()
        if nfe:
            td.insert(0,'<tr><td colspan="2">' \
                + process_errors(nfe) + '</td></tr>')

        return mark_safe('\n'.join(td))
