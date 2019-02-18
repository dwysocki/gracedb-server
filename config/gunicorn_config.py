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

# Worker type
worker_type = 'sync'

# Max requests settings - a worker restarts after handling this many
# requests. May be useful if we have memory leak problems.
# The jitter is drawn from a uniform distribution:
# randint(0, max_requests_jitter)
#max_requests = 0
#max_requests_jitter = 0

# Access log
accesslog = join(LOG_DIR, "gunicorn_access.log")
access_log_format = '%(t)s %(h)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Error log
errorlog = join(LOG_DIR, "gunicorn_error.log")
loglevel = 'debug'
capture_output = True

#forwarded_allow_ips = '127.0.0.1'
#proxy_allow_ips = '127.0.0.1'
