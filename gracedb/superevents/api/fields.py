from rest_framework import fields

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
