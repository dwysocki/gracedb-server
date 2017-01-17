
from django.http import (HttpResponse, HttpResponseRedirect, 
    HttpResponseNotFound, Http404, HttpResponseForbidden,
    HttpResponseBadRequest)
from django.conf import settings
from django.core.urlresolvers import reverse 
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils import timezone
from django.db.models import Q

from django_twilio.client import twilio_client
import socket
# Set up logger
import logging
log = logging.getLogger(__name__)

from .models import Trigger, Contact
from .forms import ContactForm, triggerFormFactory
from gracedb.permission_utils import internal_user_required, lvem_user_required
from gracedb.query import labelQuery
from gracedb.models import Label
from gracedb.alert import get_twilio_from

# Let's let everybody onto the index view.
#@internal_user_required
def index(request):
    triggers = Trigger.objects.filter(user=request.user)
    contacts = Contact.objects.filter(user=request.user)
    d = { 'triggers' : triggers, 'contacts': contacts }
    return render_to_response('profile/notifications.html',
                              d,
                              context_instance=RequestContext(request))

@lvem_user_required
def managePassword(request):
    d = { 'username': request.user.username }
    if request.method == "POST":
        password = User.objects.make_random_password(length=20)
        d['password'] = password
        request.user.set_password(password)
        request.user.date_joined = timezone.now()
        request.user.save()
    return render_to_response('profile/manage_password.html',
                              d,
                              context_instance=RequestContext(request))

@internal_user_required
def create(request):
    explanation = ""
    message = ""
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


            if len(label_query) > 0 and labels.count() > 0:
                msg = "Cannot both select labels and define label query. Choose one or the other." 
                return HttpResponseBadRequest(msg)

            # If we've got a label query defined for this trigger, then we want 
            # each label mentioned in the query to be listed in the events labels.
            # It would be smarter to make sure the label isn't being negated, but 

            # we can just leave that for later.
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

            if contacts and (labels or pipelines):
                t.save() # Need an id before relations can be set.
                try:
                    t.labels = labels
                    t.pipelines = pipelines
                    t.contacts = contacts
                    t.farThresh = farThresh
                    t.label_query = label_query
                except:
                    t.delete()
                t.save()
                request.session['flash_msg'] = "Created: %s" % t.userlessDisplay()
                return HttpResponseRedirect(reverse(index))
        # Data was bad
        try:
            if not contacts:
                message += "You must specify at least one contact. "
            if not (labels or pipelines):
                message += "You need to indicate label(s) and/or pipeline(s)."
        except NameError:
            # form is not valid, so labels, contacts and pipelines were not set.
            # hopefully, there are error messages in the form.
            pass
    else:
        form = triggerFormFactory(user=request.user)
    if message:
        request.session['flash_msg'] = message
    return render_to_response('profile/createNotification.html',
                              { "form" : form,
                                "creating":"Notification",
                                "explanation": explanation,
                              },
                              context_instance=RequestContext(request))

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
        return HttpResponseForbidden("NO!")
    request.session['flash_msg'] = "Notification Deleted: %s" % t.userlessDisplay()
    t.delete()
    return index(request)

#--------------
#-- Contacts --
#--------------

@internal_user_required
def createContact(request):
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
            request.session['flash_msg'] = "Created: %s" % c
            return HttpResponseRedirect(reverse(index))
    else:
        form = ContactForm()
    return render_to_response('profile/createNotification.html',
                              { "form": form,
                                "creating": "Contact",
                              },
                              context_instance=RequestContext(request))

@internal_user_required
def testContact(request, id):
    """Users can test their Contacts through the web interface"""
    try:
        c = Contact.objects.get(id=id)
    except Contact.DoesNotExist:
        raise Http404
    if request.user != c.user:
        return HttpResponseForbidden("Can't edit a Contact that isn't yours.")
    else:
        flash_msg = 'Testing contact "{0}".'.format(c.desc)
        hostname = socket.gethostname()
        if c.email:
            # Send test e-mail
            try:
                subject = 'Test of contact "{0}" from {1}' \
                          .format(c.desc, hostname)
                message = ('This is a test of contact "{0}" from '
                           'https://{1}.ligo.org.').format(c.desc, hostname)
                email = EmailMessage(subject, message, settings.SERVER_EMAIL, 
                                     [c.email], [])
                email.send()
                log.debug('Sent test e-mail to {0}'.format(c.email))
            except:
                flash_msg += " Error sending test e-mail to {0}." \
                             .format(c.email)
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
            except:
                flash_msg += " Error contacting {0}.".format(c.phone)
                log.exception('Error contacting {0}'.format(c.phone))

        request.session['flash_msg'] = flash_msg
        return index(request)

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
        return HttpResponseForbidden("NO!")
    request.session['flash_msg'] = "Notification Deleted: %s" % c
    c.delete()
    return index(request)

