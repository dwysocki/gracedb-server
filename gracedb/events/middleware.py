from django.urls import resolve
import logging
logger = logging.getLogger(__name__)

class PerformanceMiddleware(object):

    def __init__(self, get_response):
        # Custom logger for this middleware 
        self.logger = logging.getLogger('performance')

        self.get_response = get_response
        super(PerformanceMiddleware, self).__init__()

    def __call__(self, request):

        # Request processing code ---------------------------------------------

        # Get response --------------------------------------------------------
        response = self.get_response(request)

        # Response processing code --------------------------------------------

        # Determine whether the user tried to create or replace an event.
        # If the URL isn't among the URLs known to Django, we just return the response.
        try:
            url_name = resolve(request.path_info).url_name
        except:
            return response

        create = False
        if url_name=='create':
            create = True
        elif url_name=='event-list' and request.method=='POST':
            create = True
        elif url_name=='event-detail' and request.method=='PUT':
            create = True

        # Determine whether the user tried to annotate an event.
        annotate = False
        if url_name=='logentry':
            annotate = True
        elif url_name=='eventlog-list' and request.method=='POST':
            annotate = True

        # XXX If both are true, something is really wrong and there should
        # be an error message.
        if create and annotate:
            return response

        username = ''
        try:
            username = request.user.username
        except:
            pass

        if create:
            # Log the status.
            self.logger.info("create: %d: %s" % (response.status_code, username))
        elif annotate:
            self.logger.info("annotate: %d: %s" % (response.status_code, username))
        
        if response.status_code == 429:
            request_logger = logging.getLogger('django.request')
            msg = '%s to %s limited for user: %s' % (request.method, url_name, username)
            request_logger.error(msg)

        return response
