from django.core.urlresolvers import resolve
import logging

class PerformanceMiddleware:

    def process_response(self, request, response):
        # Determine whether the user tried to create or replace an event.
        logger = logging.getLogger(__name__)
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
            logger.info("create: %d: %s" % (response.status_code, username))
        elif annotate:
            logger.info("annotate: %d: %s" % (response.status_code, username))
        
        if response.status_code == 429:
            request_logger = logging.getLogger('django.request')
            msg = '%s to %s limited for user: %s' % (request.method, url_name, username)
            request_logger.error(msg)

        return response
