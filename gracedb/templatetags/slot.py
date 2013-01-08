
from django import template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from ..models import Slot, EventLog
register = template.Library()

@register.filter("slot")
def slot(event,slotname):
    if event is None:
        return mark_safe("")
    try:
        slot = Slot.objects.filter(event=event).filter(name=slotname)[0]
        out = slot.value
    except:
        return mark_safe("Object not found.")
    return mark_safe(out)

