from django.utils.deprecation import MiddlewareMixin
# From http://www.djangosnippets.org/snippets/708/
# splits up request's accepted types for easy access.
#
# Added try/except to handle case of no HTTP_ACCEPT header

class AcceptMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            acc = [a.split(';')[0] for a in request.META['HTTP_ACCEPT'].split(',')]
        except:
            acc = ['text/html']
        setattr(request, 'accepted_types', acc )
        request.accepts = lambda type: type in acc
        return None
