# To run this manually (not via systemd):
#   gunicorn --config config/gunicorn_config.py config.wsgi:application
# (assuming that you are in the base directory of the GraceDB server code repo)
import os
from os.path import abspath, dirname, join
import sys
import multiprocessing

# Useful function for getting environment variables
def get_from_env(envvar, default_value=None, fail_if_not_found=True):
    value = os.environ.get(envvar, default_value)
    if (value == default_value and fail_if_not_found):
        raise ImproperlyConfigured(
            'Could not get environment variable {0}'.format(envvar))
    return value

# Parameters
GUNICORN_PORT = 8080
LOG_DIR = abspath(join(dirname(__file__), "..", "..", "logs"))

# Gunicorn configuration ------------------------------------------------------
# Bind to localhost on specified port
bind = "127.0.0.1:{port}".format(port=GUNICORN_PORT)

# Number of workers -----------------------------------------------------------
# 2*CPU + 1 (recommendation from Gunicorn documentation)

workers  = get_from_env('GUNICORN_WORKERS',
                   default_value=multiprocessing.cpu_count()*2 + 1,
                   fail_if_not_found=False)

threads = get_from_env('GUNICORN_THREADS',
                   default_value=2,
                   fail_if_not_found=False)

# Worker class ----------------------------------------------------------------
# sync by default, generally safe and low-resource:
# https://docs.gunicorn.org/en/stable/design.html#sync-workers

worker_class = get_from_env('GUNICORN_WORKER_CLASS',
                   default_value='gthread',
                   fail_if_not_found=False)

# Timeout ---------------------------------------------------------------------
# If not specified, the timeout default is 30 seconds:
# https://gunicorn-docs.readthedocs.io/en/stable/settings.html#worker-processes

timeout = get_from_env('GUNICORN_TIMEOUT',
                   default_value=300,
                   fail_if_not_found=False)

# max_requests settings -------------------------------------------------------
# The maximum number of requests a worker will process before restarting.
# May be useful if we have memory leak problems.
# The jitter is drawn from a uniform distribution:
# randint(0, max_requests_jitter)

max_requests = get_from_env('GUNICORN_MAX_REQUESTS',
                   default_value=2500,
                   fail_if_not_found=False)

max_requests_jitter = get_from_env('GUNICORN_MAX_REQUESTS_JITTER',
                   default_value=100,
                   fail_if_not_found=False)

# keepalive -------------------------------------------------------------------
# The number of seconds to wait for requests on a Keep-Alive connection.
# Generally set in the 1-5 seconds range for servers with direct connection
# to the client (e.g. when you don’t have separate load balancer).
# When Gunicorn is deployed behind a load balancer, it often makes sense to set
# this to a higher value.

keepalive = get_from_env('GUNICORN_KEEPALIVE',
                   default_value=25,
                   fail_if_not_found=False)

# preload_app -----------------------------------------------------------------
# Load application code before the worker processes are forked.

# By preloading an application you can save some RAM resources as well as speed
# up server boot times. Although, if you defer application loading to each 
# worker process, you can reload your application code easily by restarting 
# workers.

# If you aren't going to make use of on-the-fly reloading, consider preloading 
# your application code to reduce its memory footprint. So, turn this on in
# production.

preload_app = get_from_env('GUNICORN_PRELOAD_APP',
                   default_value=False,
                   fail_if_not_found=False)

# Logging ---------------------------------------------------------------------
# Access log
accesslog = join(LOG_DIR, "gunicorn_access.log")
access_log_format = ('GUNICORN | %(h)s %(l)s %(u)s %(t)s '
    '"%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"')

# Error log
errorlog = join(LOG_DIR, "gunicorn_error.log")
loglevel = 'debug'
capture_output = True

# Override logger class to modify error format
from gunicorn.glogging import Logger
class CustomLogger(Logger):
    error_fmt = 'GUNICORN | ' + Logger.error_fmt
logger_class = CustomLogger
