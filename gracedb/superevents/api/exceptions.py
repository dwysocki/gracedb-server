from rest_framework.views import exception_handler

import logging
logger = logging.getLogger(__name__)

def gracedb_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Combine values into one list
    exc_out = [item for sublist in exc.detail.values() for item in sublist]

    # For only one exception, just print it rather than the list
    if len(exc_out) == 1:
        exc_out = exc_out[0]

    # Update response data
    response.data = exc_out

    return response
