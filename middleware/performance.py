from django.core.urlresolvers import resolve
import logging

class PerformanceMiddleware:

    #logging.basicConfig(filename="/home/branson/logs/performance.log",level=logging.INFO)

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

        if create:
            # Log the status.
            #logging.info("%d" % response.status_code)
            logger.info("create: %d: %s" % (response.status_code, request.user.username))
        elif annotate:
            logger.info("annotate: %d: %s" % (response.status_code, request.user.username))

        return response
