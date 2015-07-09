from rest_framework.throttling import UserRateThrottle

class PostOrPutUserRateThrottle(UserRateThrottle):

    def allow_request(self, request, view):
        """
        This is mostly copied from the Rest Framework's SimpleRateThrottle
        except we now pass the request to throttle_success
        """
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

    def wait(self):
        """
        The HTTPError exception includes a little message with the recommended
        wait time. However, this doesn't seem to work very well with fractional
        seconds. Returning 'None' will prevent it from trying to recommend a 
        wait time.
        """
        return None

class EventCreationThrottle(PostOrPutUserRateThrottle):
    scope = 'event_creation'

class AnnotationThrottle(PostOrPutUserRateThrottle):
    scope = 'annotation'

