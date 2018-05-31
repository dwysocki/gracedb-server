
from django.http import (HttpResponse, HttpResponseRedirect, 
    HttpResponseNotFound, Http404, HttpResponseForbidden,
    HttpResponseBadRequest)
from django.conf import settings
from django.urls import reverse 
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.template import RequestContext
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Q

from django.contrib import messages

from django_twilio.client import twilio_client
import socket
# Set up logger
import logging
log = logging.getLogger(__name__)

from .models import Trigger, Contact
from .forms import ContactForm, triggerFormFactory, TriggerForm
from events.permission_utils import internal_user_required, \
    lvem_user_required, is_external
from events.query import labelQuery
from events.models import Label
from alerts.old_alert import get_twilio_from

# Let's let everybody onto the index view.
#@internal_user_required
def index(request):
    triggers = Trigger.objects.filter(user=request.user)
    contacts = Contact.objects.filter(user=request.user)
    d = { 'triggers': triggers, 'contacts': contacts }

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
    """Create a notification (Trigger) via the web interface"""

    if request.method == "POST":
        form = triggerFormFactory(request.POST, user=request.user)
        if form.is_valid():
            # Create the Trigger
            t = Trigger(user=request.user)
            labels = form.cleaned_data['labels']
            pipelines = form.cleaned_data['pipelines']
            contacts = form.cleaned_data['contacts']
            farThresh = form.cleaned_data['farThresh']
            label_query = form.cleaned_data['label_query']

            # If we've got a label query defined for this trigger, then we want
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
                t.farThresh = farThresh
                t.label_query = label_query
                t.save()
                messages.info(request, 'Created notification: {n}.'.format(
                    n=t.userlessDisplay()))
            except Exception as e:
                messages.error(request, ('Error creating notification {n}: '
                    '{e}.').format(n=t.userlessDisplay(), e=e))
                t.delete()

            return HttpResponseRedirect(reverse(index))
    else:
        form = triggerFormFactory(user=request.user)
    return render(request, 'profile/createNotification.html',
        context={"form": form})

@internal_user_required
def edit(request, id):
    raise Http404

@internal_user_required
def delete(request, id):
    try:
        t = Trigger.objects.get(id=id)
    except Trigger.DoesNotExist:
        raise Http404
    if request.user != t.user:
        return HttpResponseForbidden(("You are not allowed to modify another "
            "user's notifications."))
    messages.info(request,'Notification "{nname}" has been deleted.' \
        .format(nname=t.userlessDisplay()))
    t.delete()
    return HttpResponseRedirect(reverse(index))

#--------------
#-- Contacts --
#--------------

@internal_user_required
def createContact(request):

    # Handle form.
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Create the Contact
            c = Contact(
                    user = request.user,
                    desc = form.cleaned_data['desc'],
                    email = form.cleaned_data['email'],
                    phone = form.cleaned_data['phone'],
                    call_phone = form.cleaned_data['call_phone'],
                    text_phone = form.cleaned_data['text_phone'],
                )
            c.save()
            messages.info(request, 'Created contact "{cname}".'.format(
                cname=c.desc))
            return HttpResponseRedirect(reverse(index))
    else:
        form = ContactForm()
    return render(request, 'profile/createContact.html',
        context={"form": form})

@internal_user_required
def testContact(request, id):
    """Users can test their Contacts through the web interface"""
    try:
        c = Contact.objects.get(id=id)
    except Contact.DoesNotExist:
        raise Http404
    if request.user != c.user:
        return HttpResponseForbidden("Can't test a Contact that isn't yours.")
    else:
        messages.info(request, 'Testing contact "{0}".'.format(c.desc))
        hostname = socket.gethostname()
        if c.email:
            # Send test e-mail
            try:
                subject = 'Test of contact "{0}" from {1}' \
                    .format(c.desc, hostname)
                msg = ('This is a test of contact "{0}" from '
                    'https://{1}.ligo.org.').format(c.desc, hostname)
                email = EmailMessage(subject, msg, settings.SERVER_EMAIL,
                    [c.email], [])
                email.send()
                log.debug('Sent test e-mail to {0}'.format(c.email))
            except Exception as e:
                messages.error(request, ("Error sending test e-mail to {0}: "
                    "{1}.").format(c.email, e))
                log.exception('Error sending test e-mail to {0}'.format(c.email))

        if c.phone:
            # Send test phone alert
            try:
                # Get "from" phone number.
                from_ = get_twilio_from()
                # Construct URL of TwiML bin
                if c.call_phone:
                    twiml_url = settings.TWIML_BASE_URL \
                                + settings.TWIML_BIN['test']
                    twiml_url += "?server={0}".format(hostname)
                    # Make call
                    twilio_client.calls.create(to=c.phone, from_=from_,
                        url=twiml_url, method='GET')
                    log.debug('Making test call to {0}'.format(c.phone))

                if c.text_phone:
                    twilio_client.messages.create(to=c.phone, from_=from_,
                        body=('This is a test message from https://{0}'
                              '.ligo.org.').format(hostname))
                    log.debug('Sending test text to {0}'.format(c.phone))
            except Exception as e:
                messages.error(request, "Error contacting {0}: {1}." \
                    .format(c.phone, e))
                log.exception('Error contacting {0}: {1}'.format(c.phone, e))

        return HttpResponseRedirect(reverse(index))

@internal_user_required
def editContact(request, id):
    raise Http404

@internal_user_required
def deleteContact(request, id):
    """Users can delete their Contacts through the web interface"""
    try:
        c = Contact.objects.get(id=id)
    except Contact.DoesNotExist:
        raise Http404
    if request.user != c.user:
        return HttpResponseForbidden(("You are not authorized to modify "
            "another user's Contacts."))
    messages.info(request, 'Contact "{cname}" has been deleted.' \
        .format(cname=c.desc))
    c.delete()
    return HttpResponseRedirect(reverse(index))

