from __future__ import absolute_import

from superevents.models import Superevent

# Define superevent lookup URL kwarg and regex pattern for
# use throughout this module
SUPEREVENT_LOOKUP_URL_KWARG = 'superevent_id'
SUPEREVENT_LOOKUP_REGEX = Superevent.ID_REGEX
