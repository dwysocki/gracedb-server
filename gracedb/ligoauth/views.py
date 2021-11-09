import logging

from django.conf import settings
from django.contrib.auth import (
    get_user_model, update_session_auth_hash, REDIRECT_FIELD_NAME
)
from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import RedirectView

from .decorators import lvem_observers_only


# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


# Three steps in login process:
#   1. Pre-login view where we set up all of the necessary redirects, starting
#      with the Shibboleth SSO page for login through an IdP.
#   2. Login through IdP, redirect to post-login view.
#   3. Post-login view, where Apache puts the user's attributes into the
#      request headers.  Our Django middleware and auth backends consume the
#      attributes and use them to log into a user account in the database.  The
#      user is then redirected to the original page where they logged in from.
@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ShibLoginView(SuccessURLAllowedHostsMixin, RedirectView):
    redirect_authenticated_user = True
    redirect_field_name = REDIRECT_FIELD_NAME
    post_login_view_name = 'post-login'

    def dispatch(self, request, *args, **kwargs):
        if (self.redirect_authenticated_user
            and self.request.user.is_authenticated):
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check "
                    "that your LOGIN_REDIRECT_URL doesn't point to a login "
                    "page."
                )
            return HttpResponseRedirect(redirect_to)
        return super(ShibLoginView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """User is already logged in."""
        url = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(
                self.redirect_field_name,
                resolve_url(settings.LOGIN_REDIRECT_URL)
            )
        )
        return url

    def get_redirect_url(self, *args, **kwargs):
        # Where the user should finally be redirected to
        original_url = self.get_success_url()

        # Target to pass to the shibboleth SSO page as a URL param
        shib_target = "{url}?{params}".format(
            url=reverse(self.post_login_view_name),
            params=urlencode({self.redirect_field_name: original_url})
        )

        # Full URL to redirect to right now
        full_login_url = "{base}?{params}".format(
            base=settings.SHIB_LOGIN_URL,
            params=urlencode({'target': shib_target})
        )
        return full_login_url


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ShibPostLoginView(SuccessURLAllowedHostsMixin, RedirectView):
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_redirect_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''


@lvem_observers_only(superuser_allowed=True)
def manage_password(request):
    # Set up context dictionary
    d = {}

    if request.method == "POST":
        password = UserModel.objects.make_random_password(length=20)
        d['password'] = password
        request.user.set_password(password)
        request.user.date_joined = timezone.now()
        request.user.save()
        update_session_auth_hash(request, request.user)

    if request.user.has_usable_password():
        d['has_password'] = True
        # Check if password is expired
        # NOTE: This is super hacky because we are using date_joined to store
        # the date when the password was set.
        password_expiry = request.user.date_joined + \
            settings.PASSWORD_EXPIRATION_TIME - timezone.now()
        if (password_expiry.total_seconds() < 0):
            d['expired'] = True
        else:
            d['expired'] = False
            d['expiration_days'] = password_expiry.days
    else:
        d['has_password'] = False

    return render(request, 'ligoauth/manage_password.html', context=d)
