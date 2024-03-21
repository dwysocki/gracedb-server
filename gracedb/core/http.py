# Request/response utilities
import logging
import os

from django.http import HttpResponse
from django.urls import resolve, Resolver404

from .vfile import VersionedFile

# Set up logger
logger = logging.getLogger(__name__)


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

    # Set content type (have to set both since different ones are used
    # depending on whether the response is a Django response or
    # a rest_framework response)
    response.content_type = content_type
    response['Content-Type'] = content_type

    # Set encoding (again in both places)
    if encoding is not None:
        response.encoding = encoding
        response['Content-Encoding'] = encoding

    # For binary files, add the file as an attachment (direct download instead
    # of opening in browser window). Also do this for gzipped files on the server
    # (like *.xml.gz) because their content_type shows up as the oirginal file, and
    # so the browser will fail when it tries to visualize the gzipped version. This
    # is kind of a quirk for sending gzip files, because all modern browers will 
    # Accept-Encoding: gzip from the server, regardless of the content_type. 
    # tl;dr force a download of explicit gzip files.
    if (content_type == "application/octet-stream" or encoding == "gzip"):
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
    try:
        # Check if requested file can be opened
        with open(file_path, "rb"):
            pass
        response = serve_file(file_path, ResponseClass)
    except FileNotFoundError:
        err_msg = "File {0} not found".format(os.path.basename(file_path))
        response = ResponseClass(err_msg, status=404)
    except PermissionError:
        err_msg = "Access to file {0} forbidden".format(
            os.path.basename(file_path))
        response = ResponseClass(err_msg, status=403)
    except Exception:
        err_msg = "Unhandled exception serving the file {0}".format(
            os.path.basename(file_path))
        response = ResponseClass(err_msg, status=500)

    return response
