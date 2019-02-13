import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import (
    HttpResponse, HttpResponseRedirect, HttpResponseNotFound,
    Http404, HttpResponseForbidden, HttpResponseBadRequest
)
from django.template import RequestContext
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView, DeleteView, UpdateView
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin, DetailView

from django_twilio.client import twilio_client

from core.views import MultipleFormView
from events.permission_utils import lvem_user_required, is_external
from events.models import Label
from ligoauth.decorators import internal_user_required
from .forms import (
    PhoneContactForm, EmailContactForm, VerifyContactForm,
    EventNotificationForm, SupereventNotificationForm,
)
from .models import Notification, Contact
from .phone import get_twilio_from


# Set up logger
logger = logging.getLogger(__name__)


@login_required
def index(request):
    context = {
        'notifications': request.user.notification_set.all(),
        'contacts': request.user.contact_set.all(),
    }

    return render(request, 'profile/notifications.html', context=context)


@lvem_user_required
def managePassword(request):
    # lvem_user_required only checks for LVEM group membership,
    # not the absence of LVC membership.  We want this page to be
    # forbidden to LVC members - they don't need passwords since they
    # have certificate-based access to the API.
    if not is_external(request.user):
        return HttpResponseForbidden("Forbidden")

    # Set up context dictionary
    d = { 'username': request.user.username }

    if request.method == "POST":
        password = User.objects.make_random_password(length=20)
        d['password'] = password
        request.user.set_password(password)
        request.user.date_joined = timezone.now()
        request.user.save()

    if request.user.has_usable_password():
        d['has_password'] = True
        # Check if password is expired
        # NOTE: This is super hacky because we are using date_joined to store
        # the date when the password was set.
        password_expiry = request.user.date_joined + \
            settings.PASSWORD_EXPIRATION_TIME - timezone.now()
        if (password_expiry.total_seconds() < 0):
            d['expired'] = True
        else:
            d['expired'] = False
            d['expiration_days'] = password_expiry.days
    else:
        d['has_password'] = False

    return render(request, 'profile/manage_password.html', context=d)

###############################################################################
# Notification views ##########################################################
###############################################################################
@method_decorator(internal_user_required, name='dispatch')
class CreateNotificationView(MultipleFormView):
    """Create a notification"""
    template_name = 'alerts/create_notification.html'
    success_url = reverse_lazy('alerts:index')
    form_classes = [SupereventNotificationForm, EventNotificationForm]

    def get_context_data(self, **kwargs):
        kwargs['idx'] = 0
        if (self.request.method in ('POST', 'PUT')):
            form_keys = [f.key for f in self.form_classes]
            idx = form_keys.index(self.request.POST['key_field'])
            kwargs['idx'] = idx
        return kwargs

    def get_form_kwargs(self, *args, **kwargs):
        kw = super(CreateNotificationView, self).get_form_kwargs(
            *args, **kwargs)
        kw['user'] = self.request.user
        return kw

    def form_valid(self, form):
        if form.cleaned_data.has_key('key_field'):
            form.cleaned_data.pop('key_field')

        # Add user (from request) and category (stored on form class) to
        # the form instance, then save
        form.instance.user = self.request.user
        form.instance.category = form.category
        form.save()

        # Add message and return
        messages.info(self.request, 'Created notification: {n}.'.format(
            n=form.instance.description))
        return super(CreateNotificationView, self).form_valid(form)

    superevent_form_valid = event_form_valid = form_valid


@method_decorator(internal_user_required, name='dispatch')
class EditNotificationView(UpdateView):
    """Edit a notification"""
    template_name = 'alerts/edit_notification.html'
    # Have to provide form_class, but it will be dynamically selected below in
    # get_form()
    form_class = SupereventNotificationForm
    success_url = reverse_lazy('alerts:index')

    def get_form_class(self):
        if self.object.category == Notification.NOTIFICATION_CATEGORY_EVENT:
            return EventNotificationForm
        else:
            return SupereventNotificationForm

    def get_form_kwargs(self, *args, **kwargs):
        kw = super(EditNotificationView, self).get_form_kwargs(
            *args, **kwargs)
        kw['user'] = self.request.user
        return kw

    def get_queryset(self):
        return self.request.user.notification_set.all()


@method_decorator(internal_user_required, name='dispatch')
class DeleteNotificationView(DeleteView):
    """Delete a notification"""
    model = Notification
    success_url = reverse_lazy('alerts:index')

    def get(self, request, *args, **kwargs):
        # Override this so that we don't require a confirmation page
        # for deletion
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super(DeleteNotificationView, self).delete(request, *args,
            **kwargs)
        messages.info(request, 'Notification {n} has been deleted.'.format(
            n=self.object.description))
        return response

    def get_queryset(self):
        # Queryset should only contain the user's notifications
        return self.request.user.notification_set.all()


###############################################################################
# Contact views ###############################################################
###############################################################################
@method_decorator(internal_user_required, name='dispatch')
class CreateContactView(MultipleFormView):
    """Create a contact"""
    template_name = 'alerts/create_contact.html'
    success_url = reverse_lazy('alerts:index')
    form_classes = [PhoneContactForm, EmailContactForm]

    def get_context_data(self, **kwargs):
        kwargs['idx'] = 0
        if (self.request.method in ('POST', 'PUT')):
            form_keys = [f.key for f in self.form_classes]
            idx = form_keys.index(self.request.POST['key_field'])
            kwargs['idx'] = idx
        return kwargs

    def form_valid(self, form):

        # Remove key_field, add user, and save form
        if form.cleaned_data.has_key('key_field'):
            form.cleaned_data.pop('key_field')
        form.instance.user = self.request.user
        form.save()

        # Generate message and return
        messages.info(self.request, 'Created contact "{cname}".'.format(
            cname=form.instance.description))
        return super(CreateContactView, self).form_valid(form)

    email_form_valid = phone_form_valid = form_valid


@method_decorator(internal_user_required, name='dispatch')
class EditContactView(UpdateView):
    """
    Edit a contact. Users shouldn't be able to edit the actual email address
    or phone number since that would allow them to circumvent the verification
    process.
    """
    template_name = 'alerts/edit_contact.html'
    # Have to provide form_class, but it will be dynamically selected below in
    # get_form()
    form_class = PhoneContactForm
    success_url = reverse_lazy('alerts:index')

    def get_form_class(self):
        if self.object.phone is not None:
            return PhoneContactForm
        else:
            return EmailContactForm
        return self.form_class

    def get_form(self, form_class=None):
        form = super(EditContactView, self).get_form(form_class)
        if isinstance(form, PhoneContactForm):
            form.fields['phone'].disabled = True
        elif isinstance(form, EmailContactForm):
            form.fields['email'].disabled = True
        return form

    def get_queryset(self):
        return self.request.user.contact_set.all()


@method_decorator(internal_user_required, name='dispatch')
class DeleteContactView(DeleteView):
    """Delete a contact"""
    model = Contact
    success_url = reverse_lazy('alerts:index')

    def get(self, request, *args, **kwargs):
        # Override this so that we don't require a confirmation page
        # for deletion
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super(DeleteContactView, self).delete(request, *args,
            **kwargs)
        messages.info(request, 'Contact "{cname}" has been deleted.'.format(
            cname=self.object.description))
        return response

    def get_queryset(self):
        # Queryset should only contain the user's contacts
        return self.request.user.contact_set.all()


@method_decorator(internal_user_required, name='dispatch')
class TestContactView(DetailView):
    """Test a contact (must be verified already)"""
    # Send alerts to all contact methods
    model = Contact
    success_url = reverse_lazy('alerts:index')

    def get_queryset(self):
        return self.request.user.contact_set.all()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Handle case where contact is not verified
        if not self.object.verified:
            msg = ('Contact "{desc}" must be verified before it can be '
                'tested.').format(desc=self.object.description)
            messages.info(request, msg)
            return HttpResponseRedirect(self.success_url)

        # Send test notifications
        msg = 'This is a test of contact "{desc}" from {host}.'.format(
            desc=self.object.description, host=settings.LIGO_FQDN)
        if self.object.email:
            subject = 'Test of contact "{desc}" from {host}'.format(
                desc=self.object.description, host=settings.LIGO_FQDN)
            email = EmailMessage(subject, msg, settings.ALERT_EMAIL_FROM,
                [self.object.email], [])
            email.send()
        if self.object.phone:
            # Get "from" phone number.
            from_ = get_twilio_from()
            # Send test call
            if (self.object.phone_method == Contact.CONTACT_PHONE_CALL or
                self.object.phone_method == Contact.CONTACT_PHONE_BOTH):

                # Construct URL of TwiML bin
                twiml_url = '{base}{twiml_bin}'.format(
                    base=settings.TWIML_BASE_URL,
                    twiml_bin=settings.TWIML_BIN['test'])

                # Make call
                twilio_client.calls.create(to=self.object.phone, from_=from_,
                    url=twiml_url, method='GET')

            if (self.object.phone_method == Contact.CONTACT_PHONE_TEXT or
                self.object.phone_method == Contact.CONTACT_PHONE_BOTH):
        
                twilio_client.messages.create(to=self.object.phone,
                    from_=from_, body=msg)

        # Message for web view
        messages.info(request, 'Testing contact "{desc}".'.format(
            desc=self.object.description))

        return HttpResponseRedirect(self.success_url)


@method_decorator(internal_user_required, name='dispatch')
class VerifyContactView(UpdateView):
    """Request a verification code or verify a contact"""
    template_name = 'alerts/verify_contact.html'
    form_class = VerifyContactForm
    success_url = reverse_lazy('alerts:index')

    def get_queryset(self):
        return self.request.user.contact_set.all()

    def form_valid(self, form):
        self.object.verify()
        msg = 'Contact "{cname}" successfully verified.'.format(
            cname=self.object.description)
        messages.info(self.request, msg)
        return super(VerifyContactView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(VerifyContactView, self).get_context_data(**kwargs)

        # Determine if verification code exists and is expired
        if (self.object.verification_code is not None and
            timezone.now() > self.object.verification_expiration):
            context['code_expired'] = True

        return context


@method_decorator(internal_user_required, name='dispatch')
class RequestVerificationCodeView(DetailView):
    """Redirect view for requesting a contact verification code"""
    model = Contact

    def get_queryset(self):
        return self.request.user.contact_set.all()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Handle case where contact is already verified
        if self.object.verified:
            msg = 'Contact "{desc}" is already verified.'.format(
                desc=self.object.description)
            messages.info(request, msg)
            return HttpResponseRedirect(reverse('alerts:index'))

        # Otherwise, set up verification code for contact
        self.object.generate_verification_code()

        # Send verification code
        self.object.send_verification_code()

        messages.info(request, "Verification code sent.")
        return HttpResponseRedirect(reverse('alerts:verify-contact',
            args=[self.object.pk]))
