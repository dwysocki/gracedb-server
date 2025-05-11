from django.urls import resolve
import logging
logger = logging.getLogger(__name__)

HEADER_X509 = ['X-Forwarded-Tls-Client-Cert', 'Ssl-Client-S-Dn', 'Ssl-Client-I-Dn']
HEADER_TOKEN = 'Authorization'
HEADER_WEB = 'Cookie'

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

        # Get the authentication method based on the user's request header:
        auth_type = 'noauth'
        if any(header in request.headers for header in HEADER_X509):
            auth_type = 'x509'
        elif HEADER_TOKEN in request.headers:
            auth_type = 'scitoken'
        elif HEADER_WEB in request.headers:
            auth_type = 'shibboleth'

        if create:
            # Log the status.
            self.logger.info("create: %d: %s %s" % (response.status_code, username, auth_type))
        elif annotate:
            self.logger.info("annotate: %d: %s %s" % (response.status_code, username, auth_type))
        
        return response
