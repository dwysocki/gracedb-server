from api.throttling import PostOrPutUserRateThrottle


class EventCreationThrottle(PostOrPutUserRateThrottle):
    scope = 'event_creation'


class AnnotationThrottle(PostOrPutUserRateThrottle):
    scope = 'annotation'

