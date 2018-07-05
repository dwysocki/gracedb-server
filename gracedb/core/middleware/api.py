from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

from packaging import specifiers
import logging
logger = logging.getLogger(__name__)

class CliExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if 'cli_version' in request.POST:
            response = HttpResponse(mimetype='application/json')
            # XXX JSON
            msg = str({ 'error': "Server exception: %s" % str(exception) })
            response.write(msg)
            response['Content-length'] = len(msg)
            return response
        else:
            return None


class ClientVersionMiddleware(object):
    """
    Middleware class which checks the user's IP against a list of IPs
    corresponding to instrument control rooms.  If the user appears to be
    in a control room, we add them to the corresponding control room group
    for the duration of the request.
    """
    client_string = 'gracedb-client'
    error_messages = {
        'no_header': _('Your client software is out of date - this server '
            'requires a version {sv}.'),
        'parse_error': _('Error parsing your client software version ({v}) '
            'from the request headers.'),
        'version_mismatch': _('Your client software version ({v}) is not '
            'supported by this server. Please use a version {sv}.'),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for requests ------------------------------------

        # Get user agent
        agent_header = request.META.get('HTTP_USER_AGENT',
            request.META.get('USER_AGENT', None))

        # Determine which action to take:
        #  1. If no User-Agent header, assume old client and reject
        #  2. If User-Agent header and client_string, get version and compare
        #  3. If User-Agent header and not client_string, assume browser
        #     and allow to pass
        request_allowed = True
        if request.path.startswith('/api'):
            if (agent_header is None and not
                settings.ALLOW_BLANK_USER_AGENT_TO_API):
                request_allowed = False
                msg = self.error_messages['no_header'].format(
                    sv=settings.ALLOWED_CLIENT_VERSIONS)
            elif (agent_header is not None and self.client_string in
                  agent_header):
                try:
                    version = agent_header.split(self.client_string + '/')[1]
                except Exception as e:
                    request_allowed = False
                    msg = self.error_messages['parse_error'].format(
                        v=agent_header)
                else:
                    allowed_versions = specifiers.SpecifierSet(
                        settings.ALLOWED_CLIENT_VERSIONS)
                    if not allowed_versions.contains(version):
                        request_allowed = False
                        msg = self.error_messages['version_mismatch'].format(
                            v=version, sv=settings.ALLOWED_CLIENT_VERSIONS)

        # Get response --------------------------------------------------------
        if request_allowed:
            response = self.get_response(request)
        else:
            response = HttpResponseBadRequest(msg)

        # Code to be executed for responses -----------------------------------
        return response

