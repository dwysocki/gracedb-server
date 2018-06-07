from .models import Event

def is_event(obj):
    return isinstance(obj, Event)
