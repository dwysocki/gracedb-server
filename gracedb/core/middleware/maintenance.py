from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import resolve

import logging

# Set up logger
logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware(object):
    accept_header_name = 'HTTP_ACCEPT'
    default_message = 'The site is temporarily down for maintenance.'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request -----------------------------------------------------
        if settings.MAINTENANCE_MODE is True:

            # Check if the view specifies to ignore maintenance mode
            ignore_maintenance = \
                self.check_for_ignore_maintenance_mode(request)

            if not ignore_maintenance:
                # Get message to display
                maintenance_message = self.get_message()

                accept_header = request.META.get(self.accept_header_name, None)
                if accept_header and 'text/html' in accept_header:
                    # Attempt to handle browsers
                    context = {'message': maintenance_message}
                    return render(request, 'maintenance.html', context=context,
                                  status=503)
                else:
                    # Anything else (likely client API requests)
                    return HttpResponse(maintenance_message, status=503)

        # Otherwise, get response and return with no further processing -------
        response = self.get_response(request)
        return response

    @staticmethod
    def check_for_ignore_maintenance_mode(request):
        resolver_match = resolve(request.path)
        view_func = resolver_match.func
        return view_func.__dict__.get('ignore_maintenance_mode', False)

    def get_message(self):
        message = settings.MAINTENANCE_MODE_MESSAGE
        if message is None:
            message = self.default_message
        return message
