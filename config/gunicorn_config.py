# To run this manually (not via systemd):
#   gunicorn --config config/gunicorn_config.py config.wsgi:application
# (assuming that you are in the base directory of the GraceDB server code repo)
import os
from os.path import abspath, dirname, join
import sys
import multiprocessing

# Parameters
GUNICORN_PORT = 8080
LOG_DIR = abspath(join(dirname(__file__), "..", "..", "logs"))

# Gunicorn configuration ------------------------------------------------------
# Bind to localhost on specified port
bind = "127.0.0.1:{port}".format(port=GUNICORN_PORT)

# Number of workers = 2*CPU + 1 (recommendation from Gunicorn documentation)
workers = multiprocessing.cpu_count()*2 + 1

# Worker class.
# 
worker_class = 'gthread'
threads = 2

# Adding options for timeout. Not specified, the timeout default 
# is 30 seconds. Source:
#
# https://gunicorn-docs.readthedocs.io/en/stable/settings.html#worker-processes
#
timeout = 120

# Max requests settings - a worker restarts after handling this many
# requests. May be useful if we have memory leak problems.
# The jitter is drawn from a uniform distribution:
# randint(0, max_requests_jitter)
#max_requests = 0
#max_requests_jitter = 0

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
