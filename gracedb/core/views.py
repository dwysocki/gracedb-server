from django.http import HttpResponse
from django.views.generic.edit import FormView

import logging
logger = logging.getLogger(__name__)

def heartbeat(request):
    # Do something (?) and return 200 response
    return HttpResponse()


class MultipleFormView(FormView):
    """Requires forms to inherit from core.forms.MultipleForm"""
    form_classes = []

    @property
    def form_classes(self):
        if not hasattr(self, '_form_classes'):
            self._form_classes = {f.key: f for f in self.form_class_list}
        return self._form_classes

    def get_forms(self, form_classes=None):
        if (form_classes is None):
            form_classes = self.form_classes
        return [form(**self.get_form_kwargs(form.key)) for form in form_classes]

    def get_form_kwargs(self, form_key):
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        if (self.request.method in ('POST', 'PUT')):
            key_field = self.request.POST.get('key_field', None)
            if (key_field is not None and key_field == form_key):
                kwargs.update({'data': self.request.POST,
                    'files': self.request.FILES})
        return kwargs

    def get(self, request, *args, **kwargs):
        forms = self.get_forms()
        return self.render_to_response(self.get_context_data(forms=forms))

    def post(self, request, *args, **kwargs):
        form_key = request.POST.get('key_field')
        forms = self.get_forms()
        return self._process_individual_form(form_key, forms)

    def forms_valid(self, form):
        form_valid_method = '{key}_form_valid'.format(key=form.key)
        if hasattr(self, form_valid_method):
            return getattr(self, form_valid_method)(form)
        else:
            return HttpResponseRedirect(self.success_url)

    def forms_invalid(self, forms):
        return self.render_to_response(self.get_context_data(forms=forms))

    def _get_form_by_key(self, key, forms):
        form_keys = [f.key for f in forms]
        return forms[form_keys.index(key)]

    def _process_individual_form(self, form_key, forms):
        form = self._get_form_by_key(form_key, forms)
        if form.is_valid():
            return self.forms_valid(form)
        else:
            return self.forms_invalid(forms)
