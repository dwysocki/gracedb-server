from django import forms
from models import Trigger, Contact

def triggerFormFactory(postdata=None, user=None):
    class TF(forms.ModelForm):
        farThresh = forms.FloatField(label='FAR Threshold (Hz)', required=False,
                help_text="Leave blank to recieve all events, regardless of FAR.")
        class Meta:
            model = Trigger
            exclude = ['user', 'triggerType']

        contacts = forms.ModelMultipleChoiceField(
                        queryset=Contact.objects.filter(user=user),
                        required=False
                        )

        # XXX should probably override is_valid and check for
        # truth of (atypes or labels)
        # and set field error attributes appropriately.

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
        exclude = ['user']

