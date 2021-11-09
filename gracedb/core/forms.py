from django import forms
from django.utils.translation import gettext_lazy as _

class ModelFormUpdateMixin(forms.ModelForm):
    """
    ModelForm mixin which provides the capability to update an existing model
    object with input data which is incomplete - i.e., doesn't contain all
    fields required by the form.

    Usage:
        # For a model with attributes 'attr1' and 'attr2 and a form that
        # normally requires both attributes
        data_dict = {'attr1': 'example'}
        ExampleForm(data_dict, instance=model_instance)
    """

    def __init__(self, *args, **kwargs):
        super(ModelFormUpdateMixin, self).__init__(*args, **kwargs)

        # If instance is provided, populate missing data
        if self.instance.pk is not None:
            self.populate_missing_data()

    def get_instance_data(self):
        # Should be overridden by concrete derived classes
        return NotImplemented

    def populate_missing_data(self):
        """
        Populate missing data fields from model instance.

        NOTE: the actual data dictionary is populated, not initial data,
        because missing fields in the input data would still be ignored.
        """
        if self.instance.pk is None:
            self.add_error(None, _('Model instance not found'))

        # Insert instance data for missing fields only
        instance_data = self.get_instance_data()
        for key in self.fields:
            if not key in self.data and instance_data[key]:
                self.data[key] = instance_data[key]


class MultipleForm(forms.Form):
    key = None
    key_field = forms.CharField(max_length=30, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(MultipleForm, self).__init__(*args, **kwargs)
        self.fields['key_field'].initial = self.key
