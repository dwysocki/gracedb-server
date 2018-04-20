from rest_framework.views import exception_handler

import logging
logger = logging.getLogger(__name__)

def gracedb_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        if response.data.has_key('detail'):
            response.data['detail'] = []
            for a in exc.args:
                response.data['detail'].append(a)

    return response
