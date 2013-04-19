
from django import template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from ..models import Tag, EventLog

register = template.Library()

@register.filter("getLogsForTag")
def getLogsForTag(event,name=None):
    if event is None:
        return None
    try:
        if name:
            return event.getLogsForTag(name)
        else:
            return None
    except:
        # Either there is no such tag or something went wrong.
        # In either case, we want the template to just ignore it.
        return None

@register.filter("tagUnicode")
def tagUnicode(tag):
    return unicode(tag);

@register.filter("logsForTagHaveImage")
def logsForTagAllHaveImages(event,name=None):
    if event is None:
        return None
    try:
        if name:
            loglist = event.getLogsForTag(name)
            # Start by assuming no images
            bool_rv = False 
            for log in loglist:
                # If any of the log messages do have an image
                # attached, we flip the return value to true.
                if log.hasImage():
                    bool_rv = True
                    break
            return bool_rv
        else:
            return None
    except:
        # Either there is no such tag or something went wrong.
        # In either case, we want the template to just ignore it.
        return None
   
@register.filter("logsForTagHaveText")
def logsForTagHaveText(event,name=None):
    if event is None:
        return None
    try:
        if name:
            loglist = event.getLogsForTag(name)
            bool_rv = False
            for log in loglist:
                if not log.hasImage():
                    bool_rv = True
                    break
            return bool_rv
        else:
            return None
    except:
        # Either there is no such tag or something went wrong.
        # In either case, we want the template to just ignore it.
        return None

