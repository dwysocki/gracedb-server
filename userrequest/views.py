
from django.http import HttpResponse
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.http import Http404, HttpResponseForbidden
from django.http import HttpResponseBadRequest

from django.core.urlresolvers import reverse 
from django.contrib.auth.models import User
from django.template import RequestContext
from django.shortcuts import render_to_response

from userprofile.models import Trigger, Contact

from userprofile.forms import ContactForm, triggerFormFactory

from gracedb.permission_utils import internal_user_required, lvem_user_required

from django.utils import timezone

from gracedb.query import labelQuery
from gracedb.models import Label
from django.db.models import Q

# Let's let everybody onto the index view.
#@internal_user_required
def index(request):
    triggers = Trigger.objects.filter(user=request.user)
    contacts = Contact.objects.filter(user=request.user)
    d = { 'triggers' : triggers, 'contacts': contacts }
    return render_to_response('profile/notifications.html',
                              d,
                              context_instance=RequestContext(request))


