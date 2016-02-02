"""
To function this requires the following to be installed:

TEMPLATE_CONTEXT_PROCESSORS
django.core.context_processors.request

MIDDLEWARE_CLASSES
django.contrib.sessions.middleware.SessionMiddleware

@author: Robert Conner (rtconner)
"""

# It's pretty simple. Do something like this in your view ..

# >>>request.session['flash_msg'] = 'Your changes have been save'
# >>>request.session['flash_params'] = {'type': 'success'}

# And maybe put something like this in your template
#
# {% load flash %}
# {% flash %}
#   <h2>{{ params.type }}</h2>
#   {{ msg }}
# {% endflash %}

# It also support a flash template, you can specify a file FLASH_TEMPLATE in
# your settings file and then that file will be rendered with msg and params as
# available variable. Usage for this would simply be {% flash_template %} and
# then you gotta make a template file that does whatever you like.

# Outside of that just be aware you need the Django session middleware and
# request context installed in your app to use this. 


from django import template
from django.template import resolve_variable, Context
from datetime import timedelta
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.sessions.models import Session
from django.conf import settings

register = template.Library()


def session_clear(session):
    """
    Private function, clear flash msgsfrom the session
    """
    try:
        del session['flash_msg']
    except KeyError:
        pass
    
    try:
        del session['flash_params']
    except KeyError:
        pass
    
    # Save changes to session
    if(session.session_key):
        Session.objects.save(session.session_key, session._session,
            timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE))


class RunFlashBlockNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
        
    def render(self, context):
        
        session = context['request'].session
        ret = None
        if session.get('flash_msg', False):
            ret = {'msg': session['flash_msg']}
            if 'flash_params' in session:
                ret['params'] = session.get('flash_params', False)
            session_clear(session);

        if ret is not None:
            context.update(ret)
            return self.nodelist.render(context)
        return ''


class RunFlashTemplateNode(template.Node):
    def __init__(self):
        pass
    
    def render(self, context):
        session = context['request'].session
        if session.get('flash_msg', False):
            ret = {'msg': session['flash_msg']}
            if 'flash_params' in session:
                ret['params'] = session.get('flash_params', False)
                
            session_clear(session);
            try:
                template = settings.FLASH_TEMPLATE
            except AttributeError:
                template = 'elements/flash.html'
            return render_to_string(template, dictionary=ret) 
        return ''

@register.tag(name="flash_template")
def do_flash_template(parser, token):
    """
    Call template if there is flash message in session
        
    Runs a check if there is a flash message in the session.
    If the flash message exists it calls settings.FLASH_TEMPLATE
    and passes the template the variables 'msg' and 'params'.
    Calling this clears the flash from the session automatically
    
    To set a flash msg, in a view call:
    request.session['flash_msg'] = 'sometihng'
    request.session[flash_'params'] = {'note': 'remember me'}
    
    In the template {{ msg }} and {{ params.note }} are available
    """
    return RunFlashTemplateNode()

@register.tag(name="flash")
def do_flash_block(parser, token):
    """
    A block section where msg and params are both available.
    Calling this clears the flash from the session automatically
    
    If there is no flash msg, then nothing inside this block
    gets rendered
    
    Example:
    {% flash %}
        {{msg}}<br />
        {{params.somekey}}
    {% endflash %}
    """
    nodelist = parser.parse(('endflash',))
    parser.delete_first_token()
    return RunFlashBlockNode(nodelist)
