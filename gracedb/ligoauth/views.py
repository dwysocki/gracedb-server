from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.conf import settings

def gracedb_login(request):
    full_login_url = "{base}?target={path}".format(base=settings.LOGIN_URL,
        path=urlquote(request.META.get('HTTP_REFERER', '/')))
    return HttpResponseRedirect(full_login_url)
