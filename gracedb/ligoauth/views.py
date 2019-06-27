import logging

from django.conf import settings
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import resolve_url, render
from django.urls import reverse
from django.utils import timezone

from .decorators import lvem_observers_only


# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


ORIGINAL_PAGE_KEY = 'login_from_page'

# Three steps in login process:
#   1. Pre-login view where we try to cache the page that the user was just on
#      and redirect to the Shibboleth SSO page for login through an IdP
#   2. Login through IdP, redirect to post-login view.
#   3. Post-login view, where Apache puts the user's attributes into the
#      session.  Our Django middleware and auth backends consume the attributes
#      and use them to log into a user account in the database.  The user is
#      then redirected to the original page where they logged in from.

def pre_login(request):
    """
    Sends user to settings.SHIB_LOGIN_URL (Shibboleth login) and sets up a
    redirect target to the actual login page where we parse the shib session
    attributes.  Saves the current page (where the login button was clicked
    from) in the session so that our login page can then redirect back to
    the original page.

    If original URL is not found, redirect to the home page
    """

    # Set target for SSO page to redirect to
    shib_target = reverse('post-login')

    # Get original url (page where the login button was clicked).
    # First try to get referer header. If not available, try to get the 'next
    # query string parameter (that's how the Django login_required
    # handles it)
    original_url = request.META.get('HTTP_REFERER', None)
    if original_url is None:
        original_url = request.GET.get('next',
            resolve_url(settings.LOGIN_REDIRECT_URL))

    # Store original url in session
    request.session[ORIGINAL_PAGE_KEY] = original_url

    # Set up url for shibboleth login with redirect target
    full_login_url = "{base}?target={target}".format(
        base=settings.SHIB_LOGIN_URL, target=shib_target)

    # Redirect to the shibboleth login
    return HttpResponseRedirect(full_login_url)


def post_login(request):
    """
    pre_login should redirect to the URL which corresponds to this view.

    Apache should be configured to put the Shibboleth session information into
    the request headers at this view's URL.

    The middleware should handle attribute extraction and logging in. So all
    we need to do here is redirect to the original page (where the user clicked
    the login button). If we can't seem to find that information, then just
    redirect to the home page.
    """

    original_url = request.session.get(ORIGINAL_PAGE_KEY,
        resolve_url(settings.LOGIN_REDIRECT_URL))

    # Redirect to the original url
    return HttpResponseRedirect(original_url)


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
