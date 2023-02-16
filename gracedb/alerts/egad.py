"""
Interface to the External GraceDB Alert Dispatcher (EGAD).
"""
import logging
import time

import requests

from django.conf import settings


# Set up logger
logger = logging.getLogger(__name__)

# Set up unchanging request details
url = settings.EGAD_URL
headers = {
    "X-AWS-Secrets-Manager-Key": settings.EGAD_SECRET_KEY,
}


def send_alert(payload):
    logger.debug(f"Sending alert through EGAD at {url}")
    time_start = time.perf_counter()
    r = requests.post(url, json=payload, headers=headers)
    time_elapsed = time.perf_counter() - time_start

    if r.status_code == requests.codes.ok:
        logger.debug(f"Sent alert through EGAD in {time_elapsed} sec")
    else:
        logger.warning(f"Failed to send alert through EGAD: {r}")
