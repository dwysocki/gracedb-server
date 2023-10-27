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
# bumped to 4*CPU + 1 after testing. Maybe increase this number in the cloud
# deployment? 

workers  = int(get_from_env('GUNICORN_WORKERS',
                   default_value=multiprocessing.cpu_count()*4 + 1,
                   fail_if_not_found=False))

# NOTE: it was found in extensive testing that threads > 1 are prone
# to connection lockups. Leave this at 1 for safety until there are 
# fixes in gunicorn.

# Why not sync? The sync worker is prone to timeout for long requests,
# like big queries. But gthread sends a heartbeat back to the main worker
# to keep it alive. We could just set the timeout to a really large number
# which would keep the long requests stable, but if there is a stuck worker, 
# then they would be subject to that really long timeout. It's a tradeoff. 

# All this goes away with async workers, but as of 3.2, django's ORM does support
# async, and testing failed pretty catastrophically and unreliably. 

threads = int(get_from_env('GUNICORN_THREADS',
                   default_value=1,
                   fail_if_not_found=False))

# Worker connections. Limit the number of connections between apache<-->gunicorn
# This avoids the situation 

worker_connections = workers * threads

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
                   default_value=30,
                   fail_if_not_found=False)

graceful_timeout = timeout

# max_requests settings -------------------------------------------------------
# The maximum number of requests a worker will process before restarting.
# May be useful if we have memory leak problems.
# The jitter is drawn from a uniform distribution:
# randint(0, max_requests_jitter)

max_requests = get_from_env('GUNICORN_MAX_REQUESTS',
                   default_value=5000,
                   fail_if_not_found=False)

max_requests_jitter = get_from_env('GUNICORN_MAX_REQUESTS_JITTER',
                   default_value=250,
                   fail_if_not_found=False)

# keepalive -------------------------------------------------------------------
# The number of seconds to wait for requests on a Keep-Alive connection.
# Generally set in the 1-5 seconds range for servers with direct connection
# to the client (e.g. when you don’t have separate load balancer).
# When Gunicorn is deployed behind a load balancer, it often makes sense to set
# this to a higher value.

# NOTE: force gunicorn to close its connection to apache after each request. 
# This has been the source of so many 502's. Basically in periods of high activity,
# gunicorn would hold on to open sockets with apache, and just deadlock itself:
# https://github.com/benoitc/gunicorn/issues/2917

keepalive = get_from_env('GUNICORN_KEEPALIVE',
                   default_value=0,
                   fail_if_not_found=False)

# preload_app -----------------------------------------------------------------
# Load application code before the worker processes are forked.

# By preloading an application you can save some RAM resources as well as speed
# up server boot times. Although, if you defer application loading to each 
# worker process, you can reload your application code easily by restarting 
# workers.

# If you aren't going to make use of on-the-fly reloading, consider preloading 
# your application code to reduce its memory footprint. So, turn this on in
# production. This is default set to False for development, but
# **TURN THIS TO TRUE FOR AWS DEPLOYMENT **

preload_app = get_from_env('GUNICORN_PRELOAD_APP',
                   default_value=True,
                   fail_if_not_found=False)

# Logging ---------------------------------------------------------------------
# Access log
accesslog = join(LOG_DIR, "gunicorn_access.log")
access_log_format = ('GUNICORN | %(h)s %(l)s %(u)s %(t)s '
    '"%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"')

# Error log
errorlog = join(LOG_DIR, "gunicorn_error.log")

# debug logging doesn't provide actual information. And this will 
# eliminate the "Connection closed." messages while still giving info 
# about worker restarts. 
loglevel = 'info'
capture_output = True

# using /dev/shm/ instead of /tmp for the temporary worker directory. See:
# https://pythonspeed.com/articles/gunicorn-in-docker/
# “in AWS an EBS root instance volume may sometimes hang for half a minute 
# and during this time Gunicorn workers may completely block.”
worker_tmp_dir='/dev/shm'


# Override logger class to modify error format
from gunicorn.glogging import Logger
class CustomLogger(Logger):
    error_fmt = 'GUNICORN | ' + Logger.error_fmt
logger_class = CustomLogger

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
