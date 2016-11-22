from django import forms
from models import Trigger, Contact

from gracedb.query import parseLabelQuery
from gracedb.pyparsing import ParseException

def triggerFormFactory(postdata=None, user=None):
    class TF(forms.ModelForm):
        farThresh = forms.FloatField(label='FAR Threshold (Hz)', required=False,
                help_text="Leave blank to recieve all events, regardless of FAR.")
        class Meta:
            model = Trigger
            exclude = ['user', 'triggerType']
            widgets = {'label_query': forms.TextInput(attrs={'size': 50})} 

        contacts = forms.ModelMultipleChoiceField(
                        queryset=Contact.objects.filter(user=user),
                        required=False
                        )

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

class TriggerForm(forms.ModelForm):
    class Meta:
        model = Trigger
        exclude = ['user', 'triggerType']

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['desc','email','phone']
        help_texts = {
            'phone': 'Prototype service: may not be available in the future.'
        }
