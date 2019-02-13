

class NonPriorityRouter(object):
    """For non-priority production workers in a swarm container deployment"""

    def db_for_read(self, model, **hints):
        return 'read_replica'

    def db_for_write(self, model, **hints):
        return 'default'
