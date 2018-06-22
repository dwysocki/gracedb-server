from rest_framework import fields

import six
import logging
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
    view_get_parent_method = 'get_parent'

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
            #value = serializer_field.context['view'].get_parent()
        return value


class CommaSeparatedOrListField(fields.ListField):
    default_style = {'base_template': 'input.html'}

    def __init__(self, *args, **kwargs):
        super(CommaSeparatedOrListField, self).__init__(*args, **kwargs)
        # Set form style for browsable API
        self.style = kwargs.get('style', self.default_style)

    def to_internal_value(self, data):
        # Empirical tests with HTML forms indicate that if we enter
        # something like 1,2,3 in a form, we will get something like
        # [u'1,2,3'] here.  So if we get input like that, we convert it
        # to [u'1', u'2', u'3'], then pass it to the base class's
        # to_internal_value() method. Might not be safe for cases where
        # a list contains CharFields which might have commas in them.
        if (isinstance(data, list) and len(data) == 1 and
            isinstance(data[0], six.string_types)):
            data = data[0].split(',')
        return super(CommaSeparatedOrListField, self).to_internal_value(data)

