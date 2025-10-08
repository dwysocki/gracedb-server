# Request/response utilities
import logging
import os
import time
import sentry_sdk

from django.http import HttpResponse
from django.urls import resolve, Resolver404

from .vfile import VersionedFile, FileSizeZeroError

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

    # Add UTF-8 encoding for plain text files:
    if content_type == 'text/plain':
        content_type += '; charset=UTF-8'

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


def check_and_serve_file(request, file_path, ResponseClass=HttpResponse,
    zero_bytes_check=False, zero_bytes_wait=0.05, zero_bytes_retries=3):
    """
    Checks whether a file exists and is readable. If so, the file is served.
    Does not check permissions - that should be done before this function
    is called.

    This function returns a response, so it should be called within a view,
    not from within a view subfunction or method.
    """

    # Perform zero-byte check with retries if enabled
    if zero_bytes_check:
        attempt = 0
        while attempt <= zero_bytes_retries:
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 0:

                    # Throw out a warning alerting the logger if there was a sleeping and
                    # retrying attempt that worked:
                    if 0 < attempt <= zero_bytes_retries:
                        logger.warning(
                            f"RECOVERY: file {os.path.basename(file_path)} is non-zero bytes "
                            f"after {attempt} retry attempts."
                            )

                    break  # File is non-zero, proceed
                else:
                    logger.warning(
                        f"Attempt {attempt + 1}: File size is zero for {file_path}. "
                        f"Retrying after {zero_bytes_wait} seconds..."
                    )
                    time.sleep(zero_bytes_wait)
                    attempt += 1
            except FileNotFoundError:
                return ResponseClass(f"File {os.path.basename(file_path)} not found", status=404)
            except Exception as e:
                return ResponseClass(f"Unhandled exception serving the file {os.path.basename(file_path)}", status=500)

        if attempt > zero_bytes_retries:
            # Log the incident:
            msg = f"File {file_path} remains zero bytes after {zero_bytes_retries} retries."
            logger.error(msg)

            # Send an error to sentry:
            exc = FileSizeZeroError(msg)

            with sentry_sdk.push_scope() as scope:
                scope.fingerprint = ['FileSizeZeroError']
                sentry_sdk.capture_exception(exc)

            # Return an HTTPError to the user:
            return ResponseClass(f"File {os.path.basename(file_path)} is empty or unavailable", status=409)


    # Proceed with original try-except block
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
