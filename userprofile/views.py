
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.http import Http404, HttpResponseForbidden

from django.core.urlresolvers import reverse

from django.template import RequestContext
from django.shortcuts import render_to_response

from models import Trigger, Contact

from forms import ContactForm, triggerFormFactory

def index(request):
    triggers = Trigger.objects.filter(user=request.ligouser)
    contacts = Contact.objects.filter(user=request.ligouser)
    d = { 'triggers' : triggers, 'contacts': contacts }
    return render_to_response('profile/notifications.html',
                              d,
                              context_instance=RequestContext(request))

def create(request):
    explanation = ""
    message = ""
    if request.method == "POST":
        form = triggerFormFactory(request.POST, user=request.ligouser)
        if form.is_valid():
            # Create the Trigger
            t = Trigger(user=request.ligouser)
            labels = form.cleaned_data['labels']
            atypes = form.cleaned_data['atypes']
            contacts = form.cleaned_data['contacts']

            if contacts and (labels or atypes):
                t.save() # Need an id before relations can be set.
                try:
                    t.labels = labels
                    t.atypes = atypes
                    t.contacts = contacts
                except:
                    t.delete()
                t.save()
                request.session['flash_msg'] = "Created: %s" % t.userlessDisplay()
                return HttpResponseRedirect(reverse(index))
        # Data was bad
        try:
            if not contacts:
                message += "You must specify at least one contact. "
            if not (labels or atypes):
                message += "You need to indicate label(s) and/or analysis type(s)."
        except NameError:
            # form is not valid, so labels, contacts and atypes were not set.
            # hopefully, there are error messages in the form.
            pass
    else:
        form = triggerFormFactory(user=request.ligouser)
    if message:
        request.session['flash_msg'] = message
    return render_to_response('profile/createNotification.html',
                              { "form" : form,
                                "creating":"Notification",
                                "explanation": explanation,
                              },
                              context_instance=RequestContext(request))

def edit(request, id):
    raise Http404

def delete(request, id):
    try:
        t = Trigger.objects.get(id=id)
    except Trigger.DoesNotExist:
        raise Http404
    if request.ligouser != t.user:
        return HttpResponseForbidden("NO!")
    request.session['flash_msg'] = "Notification Deleted: %s" % t.userlessDisplay()
    t.delete()
    return index(request)

#--------------
#-- Contacts --
#--------------

def createContact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Create the Contact
            c = Contact(
                    user=request.ligouser,
                    desc = form.cleaned_data['desc'],
                    email = form.cleaned_data['email']
                )
            c.save()
            request.session['flash_msg'] = "Created: %s" % c
            return HttpResponseRedirect(reverse(index))
    else:
        form = ContactForm()
    return render_to_response('profile/createNotification.html',
                              { "form" : form,
                                "creating":"Contact",
                               },
                              context_instance=RequestContext(request))


def editContact(request, id):
    raise Http404

def deleteContact(request, id):
    try:
        c = Contact.objects.get(id=id)
    except Contact.DoesNotExist:
        raise Http404
    if request.ligouser != c.user:
        return HttpResponseForbidden("NO!")
    request.session['flash_msg'] = "Notification Deleted: %s" % c
    c.delete()
    return index(request)

