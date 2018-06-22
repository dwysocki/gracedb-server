# mixins for class-based views

from django.conf import settings

from .permission_utils import is_external

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

        # Determine "human-readable" FAR to display
        display_far_hr = display_far
        if display_far:
            # FAR in units of yr^-1
            far_yr = display_far * (86400*365.25)
            if (far_yr < 1):
                display_far_hr = "1 per {0:0.5g} years".format(1.0/far_yr)
            else:
                display_far_hr = "{0:0.5g} per year".format(far_yr)

        return display_far, display_far_hr, far_is_upper_limit 
