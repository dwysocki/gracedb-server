from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import authentication, exceptions


UserModel = get_user_model()

# We do not want to handle authentication here because it has already
# been taken care of by Apache/Shib or Apache/mod_ssl. Moreover the
# auth middleware has already added a user to the request object. To
# play well with the django rest framework, we need to pretend like we
# authenticated the user. Remember that the request object here is a
# *wrapped* version of the Django request, so we have to dig inside it
# for the user.
class LigoAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        user = None
        try:
            user = request._request.user
        except:
            pass

        if isinstance(user, UserModel):
            return (user, None)
        else:
            raise exceptions.AuthenticationFailed(_('Bad user'))


