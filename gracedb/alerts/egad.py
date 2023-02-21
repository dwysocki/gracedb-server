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
url = f"{settings.EGAD_URL}/{settings.TIER}"
headers = {
    "X-Api-Key": settings.EGAD_API_KEY,
}


def send_alert(alert_type, payload):
    logger.debug(f"Sending alert through EGAD at {url}")
    time_start = time.perf_counter()
    r = requests.post(f"{url}/{alert_type}", json=payload, headers=headers)
    time_elapsed = time.perf_counter() - time_start

    if r.status_code == requests.codes.ok:
        logger.debug(f"Sent {alert_type} alert through EGAD in {time_elapsed} sec")
    else:
        logger.warning(f"Failed to send {alert_type} alert through EGAD: {r}")
