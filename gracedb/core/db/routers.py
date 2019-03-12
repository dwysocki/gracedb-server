import logging

from django.conf import settings


# Set up logger
logger = logging.getLogger(__name__)


class NonPriorityRouter(object):
    """For non-priority production workers in a swarm container deployment"""

    def db_for_read(self, model, **hints):
        # For API throttle caches and sessions, we want to always read out
        # of the master (or use a separate database)
        if (model._meta.db_table == settings.CACHES['throttles']['LOCATION']):
            return 'default'
        elif (model._meta.app_label == 'user_sessions' and
            model._meta.model_name == 'session'):
            return 'default'

        # Otherwise, use the read replica
        return 'read_replica'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True
