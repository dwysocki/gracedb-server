from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

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

