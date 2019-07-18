import logging

# Set up logger
logger = logging.getLogger(__name__)


class XForwardedForMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request -----------------------------------------------------
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            request.META['REMOTE_ADDR'] = \
                request.META['HTTP_X_FORWARDED_FOR'].split(",")[0].strip()

        # Get response --------------------------------------------------------
        response = self.get_response(request)

        # Process response ----------------------------------------------------

        # Return response -----------------------------------------------------
        return response
