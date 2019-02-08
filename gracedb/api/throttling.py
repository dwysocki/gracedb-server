from django.core.cache import caches

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


# NOTE: we have to use database-backed throttles to have a centralized location
# where multiple workers (like in the production instance) can access and
# update the same throttling information.


###############################################################################
# Base throttle classes #######################################################
###############################################################################
class DbCachedThrottleMixin(object):
    """Uses a non-default (database-backed) cache"""
    cache = caches['throttles']


###############################################################################
# Throttles for unauthenticated users #########################################
###############################################################################
class BurstAnonRateThrottle(DbCachedThrottleMixin, AnonRateThrottle):
    scope = 'anon_burst'


class SustainedAnonRateThrottle(DbCachedThrottleMixin, AnonRateThrottle):
    scope = 'anon_sustained'


###############################################################################
# Throttles for authenticated users #########################################
###############################################################################
class PostOrPutUserRateThrottle(DbCachedThrottleMixin, UserRateThrottle):

    def allow_request(self, request, view):
        """
        This is mostly copied from the Rest Framework's SimpleRateThrottle
        except we now pass the request to throttle_success
        """

        # Don't throttle superusers - causes problems with client
        # integration tests
        if request.user.is_superuser:
            return True

        # We don't want to throttle any safe methods
        if request.method not in ['POST', 'PUT']:
            return True

        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any requests from the history which have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return self.throttle_success(request)

    def throttle_success(self, request):
        """
        Inserts the current request's timestamp along with the key
        into the cache. Except we only do this if the request is a
        writing method (POST or PUT). That's why we needed the request.
        """
        if request.method in ['POST', 'PUT']:
            self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True
