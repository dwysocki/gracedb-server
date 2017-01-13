from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text

from .models import Trigger, Contact
from gracedb.query import parseLabelQuery
from gracedb.pyparsing import ParseException

def triggerFormFactory(postdata=None, user=None):
    class TF(forms.ModelForm):
        farThresh = forms.FloatField(label='FAR Threshold (Hz)', required=False,
                help_text="Leave blank to receive all events, regardless of FAR.")
        class Meta:
            model = Trigger
            fields = ['contacts', 'pipelines', 'farThresh', 'labels', 'label_query']
            widgets = {'label_query': forms.TextInput(attrs={'size': 50})} 

            help_texts = {
               'label_query': 'Label names can be combined with binary AND: \'&amp;\' or \',\'; or binary OR: \'|\'. For N labels, there must be exactly N-1 binary operators. Parentheses are not allowed. Additionally, any of the labels in a query string can be negated with \'~\' or \'-\'. Labels can either be selected with the select box at the top, or a query can be specified, <i>but not both</i>.'
            }

        contacts = forms.ModelMultipleChoiceField(
                        queryset=Contact.objects.filter(user=user),
                        required=False,
                        help_text="If blank, go back and create a Contact first.")
    
        # XXX should probably override is_valid and check for
        # truth of (atypes or labels)
        # and set field error attributes appropriately.

        def clean(self):
            cleaned_data = super(TF, self).clean()
            label_query = self.cleaned_data['label_query']
            if len(label_query) > 0:
                # now try parsing it
                try:
                    parseLabelQuery(label_query)
                except ParseException:
                    raise forms.ValidationError("Invalid label query.")
            return cleaned_data

    if postdata is not None:
        return TF(postdata)
    else:
        return TF()


# 11/29/2016 (TP): pretty sure this is deprecated in favor of
# triggerFormFactory; may remove at a later date.
class TriggerForm(forms.ModelForm):
    class Meta:
        model = Trigger
        exclude = ['user', 'triggerType']

class ContactForm(forms.ModelForm):
    # Adjust labels.
    desc = forms.CharField(label='Description')
    call_phone = forms.BooleanField(label='Call', initial=False, required=False)
    text_phone = forms.BooleanField(label='Text', initial=False, required=False)

    class Meta:
        model = Contact
        fields = ['desc','email','phone','call_phone','text_phone']
        help_texts = {
            'phone': 'Prototype service: may not be available in the future.'
        }

    def clean(self):
        cleaned_data = super(ContactForm, self).clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        call_phone = cleaned_data.get('call_phone')
        text_phone = cleaned_data.get('text_phone')

        # Make sure at least one contact method is provided.
        if not email and not phone:
            self.add_error(None,
                "At least one contact method (email, phone) is required.")

        # If using phone, require 'call' or 'text' (or both) to be chosen.
        if phone and not (call_phone or text_phone):
            self.add_error('phone',
                'Choose "call" or "text" (or both) for phone alerts.')

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
                                               force_text(self[field].errors),
                                               "text")
        # Phone number
        table_data['phone'] = (row_head + row_err +
            '<input id="id_{0}" name="{0}" type="text" />').format(
            'phone',self['phone'].label,force_text(self['phone'].errors))
        #table_data['phone'] = ('<tr><th><label for="id_{0}">{1}:</label></th>'
        #    + '<td><input id="id_{0}" name="{0}" type="text" />'
        #    .format('phone',self['phone'].label))
        # Add call/text checkboxes.
        table_data['phone'] += '<br />'
        for field in ['call_phone','text_phone']:
            table_data['phone'] += ('{1}?<input id="id_{0}" name="{0}"'
                           'type="checkbox" />&nbsp;&nbsp;'
                           .format(field,self[field].label))
        # Add phone help text.
        table_data['phone'] += ('<br /><span class="helptext">{0}</span>'
            '</td></tr>\n'.format(self['phone'].help_text))

        # Add errors.
        # NEED TO FIX THIS
        test = ''.join([force_text(e) for e in self.non_field_errors()])
        #table_data.insert(0,'<tr><td colspan="2">'
        #                    + force_text(self.non_field_errors())
        #                    + force_text(test))

        td = [table_data[k] for k in ['desc','email','phone']]
        if test:
           td.insert(0,'<tr><td colspan="2"><ul><li>' + force_text(test) + '</li></ul></tr></td>')

        return mark_safe('\n'.join(td))
