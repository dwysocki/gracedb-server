# Request/response utilities
from django.http import HttpResponse

from .vfile import VersionedFile

import os


def serve_file(file_path, ResponseClass=HttpResponse):
    """
    Take an absolute path to a file and construct a response.
    Files are served by Apache through X-Sendfile.

    If a certain response class is desired, it can be passed as an argument.
    Typically will be django.http.HttpResponse or
    rest_framework.response.Response.

    This function does NOT check that the file exists and is readable,
    or whether the user should be allowed to download the file.
    """

    # Try to guess file content type; if unknown, set as octet-stream
    content_type, encoding = VersionedFile.guess_mimetype(file_path)
    content_type = content_type or "application/octet-stream"

    # Set up response object
    response = ResponseClass()

    # Configure response to have Apache serve the file with X-Sendfile
    response['X-Sendfile'] = file_path

    # For binary files, add the file as an attachment (direct download instead
    # of opening in browser window)
    if content_type == "application/octet-stream":
        response['Content-Disposition'] = 'attachment; filename="{0}"'.format(
            os.path.basename(file_path))

    return response


def check_and_serve_file(request, file_path, ResponseClass=HttpResponse):
    """
    Checks whether a file exists and is readable. If so, the file is served.
    Does not check permissions - that should be done before this function
    is called.

    This function returns a response, so it should be called within a view,
    not from within a view subfunction or method.
    """

    if not os.path.exists(file_path):
        err_msg = "File {0} not found".format(os.path.basename(file_path))
        # File not found - return 404 NOT FOUND response
        response = ResponseClass(err_msg, status=404)
    elif not os.access(file_path, os.R_OK):
        err_msg = "File {0} is not readable".format(
            os.path.basename(file_path))
        # File not readable - return 500 SERVER ERROR response
        response = ResponseClass(err_msg, status=500)
    elif os.path.isfile(file_path):
        response = serve_file(file_path, ResponseClass)

    return response
