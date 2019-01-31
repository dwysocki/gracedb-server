import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db.models import Q
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
from search.query.labels import labelQuery
from .forms import (
    PhoneContactForm, EmailContactForm, VerifyContactForm,
    notificationFormFactory,
)
from .models import Notification, Contact
from .phone import get_twilio_from


# Set up logger
logger = log = logging.getLogger(__name__)



@login_required
def index(request):
    notifications = Notification.objects.filter(user=request.user)
    contacts = Contact.objects.filter(user=request.user)
    d = { 'notifications': notifications, 'contacts': contacts }

    return render(request, 'profile/notifications.html', context=d)


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


@internal_user_required
def create(request):
    """Create a notification (Notification) via the web interface"""

    if request.method == "POST":
        form = notificationFormFactory(request.POST, user=request.user)
        if form.is_valid():
            # Create the Notification
            t = Notification(user=request.user)
            labels = form.cleaned_data['labels']
            pipelines = form.cleaned_data['pipelines']
            contacts = form.cleaned_data['contacts']
            far_threshold = form.cleaned_data['far_threshold']
            label_query = form.cleaned_data['label_query']

            # TODO: properly handle negated labels
            # If we've got a label query defined for this notification, then we want
            # each label mentioned in the query to be listed in the event's
            # labels. It would be smarter to make sure the label isn't being
            # negated, but we can just leave that for later.
            if len(label_query) > 0:
                toks = labelQuery(label_query, names=True)
                f = Q()
                for tok in toks:
                    # Note that all labels are being combined with OR
                    if isinstance(tok,Q):
                        f = f | tok
                if len(f)==0:
                    return HttpResponseBadRequest("Please enter a valid label query.")
                labels = Label.objects.filter(f)

            # If the form is valid, then we have at least one contact and
            # either a label or pipeline.
            # So let's create the contact object.

            # Can't access many-to-many relationships before object is saved
            t.save()

            # Now populate fields
            try:
                t.labels = labels
                t.pipelines = pipelines
                t.contacts = contacts
                t.far_threshold = far_threshold
                t.label_query = label_query
                t.save()
                messages.info(request, 'Created notification: {n}.'.format(
                    n=t.userlessDisplay()))
            except Exception as e:
                messages.error(request, ('Error creating notification {n}: '
                    '{e}.').format(n=t.userlessDisplay(), e=e))
                t.delete()

            return HttpResponseRedirect(reverse('alerts:index'))
    else:
        form = notificationFormFactory(user=request.user)
    return render(request, 'profile/createNotification.html',
        context={"form": form})

@internal_user_required
def edit(request, id):
    raise Http404

@internal_user_required
def delete(request, id):
    try:
        t = Notification.objects.get(id=id)
    except Notification.DoesNotExist:
        raise Http404
    if request.user != t.user:
        return HttpResponseForbidden(("You are not allowed to modify another "
            "user's notifications."))
    messages.info(request,'Notification "{nname}" has been deleted.' \
        .format(nname=t.userlessDisplay()))
    t.delete()
    return HttpResponseRedirect(reverse('alerts:index'))


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
