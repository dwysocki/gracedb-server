from django.utils.http import urlquote
from django.conf import settings

def shib_login_url(request):
    target = urlquote(request.get_full_path())
    login_url = '%s?target=%s' % (settings.LOGIN_URL, target) 
    return {'login_url' : login_url}
