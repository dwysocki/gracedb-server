from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter(is_safe=True)
def confirmation_text(form_action):

    scenario, sid = form_action.split(',')

    if scenario == 'create_advocate_signoff':
        message = 'You are attempting to create an Advocate Sign-Off for {}, which ' \
                  'will generate a public alert. Do you wish to continue?'
    elif scenario == 'delete_advocate_signoff':
        message = 'You are attempting to delete an Advocate Sign-Off for {}. Do ' \
                  'you wish to continue?'
    elif scenario == 'update_advocate_signoff':
        message = 'You are attempting to update an Advocate Sign-Off for {}. Do ' \
                  'you wish to continue?'
    else:
        message = 'There should be a message here for {}.'

    return message.format(sid)
