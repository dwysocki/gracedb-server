from __future__ import absolute_import
import decimal
import logging

from django.utils import six

from rest_framework import fields

# Set up logger
logger = logging.getLogger(__name__)


class CustomHiddenDefault(fields.CurrentUserDefault):
    context_key = None

    def __init__(self, *args, **kwargs):
        self.context_key = kwargs.pop('context_key', None)

    def set_context(self, serializer_field):
        self.custom_field = self.get_field_value(serializer_field)

    def __call__(self, context_key=None):
        return self.custom_field

    def get_field_value(self, serializer_field):
        # Derived classes will probably want to override this
        value = serializer_field.context.get(self.context_key, None)
        return value


class ParentObjectDefault(CustomHiddenDefault):
    view_get_parent_method = 'get_parent_object'

    def __init__(self, *args, **kwargs):
        super(ParentObjectDefault, self).__init__(*args, **kwargs)
        method = kwargs.pop('view_get_parent_method', None)
        if method:
            self.view_get_parent_method = method

    def get_field_value(self, serializer_field):
        value = super(ParentObjectDefault, self).get_field_value(
            serializer_field)
        if not value:
            value = getattr(serializer_field.context['view'],
                self.view_get_parent_method)
            if callable(value):
                value = value()
        return value


class DelimitedOrListField(fields.ListField):
    default_style = {'base_template': 'input.html'}
    initial = '' # prevent '[]' being shown in default form in web
    delim = ','

    def __init__(self, *args, **kwargs):
        # Allow delimiter to be set dynamically
        delim = kwargs.pop('delim', None)
        if delim:
            self.delim = delim

        # Base class init
        super(DelimitedOrListField, self).__init__(*args, **kwargs)
        # Set form style for browsable API
        self.style = kwargs.get('style', self.default_style)

    def to_internal_value(self, data):
        # Empirical tests with HTML forms indicate that if we enter
        # something like 1,2,3 in a form, we will get something like
        # [u'1,2,3'] here.  So if we get input like that, we convert it
        # to [u'1', u'2', u'3'], then pass it to the base class's
        # to_internal_value() method. Not safe for cases where a list
        # contains CharFields that have commas in them.
        if (data == ['']):
            # Handle case with no input: we get [''] here as data, so
            # we convert it to an empty list.
            data = []
        elif (isinstance(data, list) and len(data) == 1 and
            isinstance(data[0], six.string_types)):
            data = data[0].split(self.delim)
        return super(DelimitedOrListField, self).to_internal_value(data)


class ChoiceDisplayField(fields.ChoiceField):
    """
    Same as standard choice field, but return a choice's display_value
    instead of the key when serializing the field.
    """

    def to_representation(self, value):
        return self._choices[value]


class GenericField(fields.Field):
    # Field, property, or callable of the object which will be used to
    # generate the representation of the object.
    to_repr = None
    lookup_field = 'id'
    model = None

    def __init__(self, *args, **kwargs):
        self.to_repr = kwargs.pop('to_repr', self.to_repr)
        self.lookup_field = kwargs.pop('lookup_field', self.lookup_field)
        self.model = kwargs.pop('model', self.model)

        assert self.to_repr is not None, ('Must specify to_repr')
        assert self.model is not None, ('Must specify model')
        super(GenericField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        value = getattr(obj, self.to_repr)

        # Handle case where we are given a function instead of
        # a model field or a property
        if callable(value):
            value = value()
        return value

    def to_internal_value(self, data):
        model_dict = self.get_model_dict(data)
        try:
            return self.model.objects.get(**model_dict)
        except self.model.DoesNotExist:
            error_msg = '{model} with {lf}={data} does not exist' \
                .format(model=self.model.__name__, lf=model_dict.keys()[0],
                data=model_dict.values()[0])
            raise serializers.ValidationError(error_msg)

    def get_model_dict(self, data):
        return {self.lookup_field: data}


class CustomDecimalField(fields.DecimalField):

    def to_internal_value(self, data):
        # Proper handling of floats: convert to quantized decimal.Decimal
        # and then back to a string, so that the rest of the processing
        # can continue
        if isinstance(data, float):
            data = decimal.Decimal(data).quantize(
                decimal.Decimal(10)**(-1 * self.decimal_places))
            data = data.to_eng_string()

        return super(CustomDecimalField, self).to_internal_value(data)
