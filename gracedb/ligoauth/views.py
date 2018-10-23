from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse

import logging
logger = logging.getLogger(__name__)


ORIGINAL_PAGE_KEY = 'login_from_page'


def pre_login(request):
    """
    Sends user to settings.LOGIN_URL (Shibboleth login) and sets up a
    redirect target to the actual login page where we parse the shib session
    attributes.  Saves the current page (where the login button was clicked
    from) in the session so that our login page can then redirect back to
    the original page.

    If original URL is not found, redirect to the home page
    """

    # Set target for shibboleth to redirect to
    shib_target = reverse('post-login')

    # Get original url (page where the login button was clicked)
    original_url = request.META.get('HTTP_REFERER', reverse('home'))

    # Store original url in session
    request.session[ORIGINAL_PAGE_KEY] = original_url

    # Set up url for shibboleth login with redirect target
    full_login_url = "{base}?target={target}".format(base=settings.LOGIN_URL,
        target=shib_target)

    # Redirect to the shibboleth login
    return HttpResponseRedirect(full_login_url)


def shib_login(request):
    """
    pre_login should redirect to the URL which corresponds to this view.

    Apache should be configured to put the Shibboleth session information into
    the request headers at this view's URL.

    The middleware should handle attribute extraction and logging in. So all
    we need to do here is redirect to the original page (where the user clicked
    the login button). If we can't seem to find that information, then just
    redirect to the home page.
    """

    original_url = request.session.get(ORIGINAL_PAGE_KEY, reverse('home'))

    # Redirect to the original url
    return HttpResponseRedirect(original_url)


def shib_logout(request):

    # Call Django logout function
    logout(request)

    # Get original url where the logout button was pressed from
    original_url = request.META.get('HTTP_REFERER', reverse('home'))

    return HttpResponseRedirect(original_url)
