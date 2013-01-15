
from django import template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from ..models import Slot, EventLog
register = template.Library()

@register.filter("slot")
def slot(event,name=None):
    if event is None:
        return None
    try:
        if name:
            return Slot.objects.filter(event=event).filter(name__exact=name)[0]
        else:
            return Slot.objects.filter(event=event)
    except:
        # Either there is no such slot or something went wrong.
        # In either case, we want the template to just ignore it.
        return None

