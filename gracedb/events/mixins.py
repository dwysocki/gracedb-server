# mixins for class-based views

from django.conf import settings

from .permission_utils import is_external
from core.utils import display_far_hz_to_yr

class DisplayFarMixin(object):

    def get_display_far(self, obj=None):
        # obj should be an Event object
        if obj is None:
            obj = self.object
        user = self.request.user

        # Determine FAR to display
        display_far = obj.far
        far_is_upper_limit = False
        if (display_far and is_external(user) and 
            display_far < settings.VOEVENT_FAR_FLOOR):

            display_far = settings.VOEVENT_FAR_FLOOR
            far_is_upper_limit = True

        return display_far, display_far_hz_to_yr(display_far), far_is_upper_limit 
