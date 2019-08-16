try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import pytest
import types

from alerts.models import Notification
from alerts.recipients import (
    CreationRecipientGetter, UpdateRecipientGetter,
    LabelAddedRecipientGetter, LabelRemovedRecipientGetter,
)
from events.models import Label, Group, Pipeline, Search
from .constants import (
    DEFAULT_FAR_T, DEFAULT_LABELS, DEFAULT_LABEL_QUERY, LABEL_QUERY2,
    RANDOM_LABEL, DEFAULT_GROUP, DEFAULT_PIPELINE, DEFAULT_SEARCH
)

# NOTE: there are a *LOT* of tests in here. It's definitely overkill.
#   I'm trying to test *every* possible situation because users tend
#   to get worked up over problems with notifications.
#
# NOTE on debugging: because there are only a few actual test functions, but
#   they are highly parametrized, it can be hard to debug failing tests. I
#   suggest looking at the test label in the pytest output (i.e., you should
#   see something like "notif_descs###", where ### is the test number). Then
#   go and edit the dataset used in the parametrize decorator to be just that
#   test.  Ex: if test_event_update_alerts with notif_descs123 is failing,
#   go and edit EVENT_UPDATE_ALERT_DATA -> EVENT_UPDATE_ALERT_DATA[123:124]


###############################################################################
# TEST DATA ###################################################################
###############################################################################
SUPEREVENT_CREATION_ALERT_DATA = [
    (None, False, ['all']),
    (None, True, ['all', 'nscand_only']),
    (DEFAULT_FAR_T*2.0, False, ['all']),
    (DEFAULT_FAR_T*2.0, True, ['all', 'nscand_only']),
    (DEFAULT_FAR_T/2.0, False, ['all', 'far_t_only']),
    (DEFAULT_FAR_T/2.0, True, ['all', 'far_t_only', 'nscand_only',
                               'far_t_and_nscand']),
]

EVENT_CREATION_ALERT_DATA = [
    (None, False, False, ['all']),
    (None, False, True, ['all', 'gps_only']),
    (None, True, False, ['all', 'nscand_only']),
    (None, True, True, ['all', 'nscand_only', 'gps_only', 'nscand_and_gps']),
    (DEFAULT_FAR_T*2.0, False, False, ['all']),
    (DEFAULT_FAR_T*2.0, False, True, ['all', 'gps_only']),
    (DEFAULT_FAR_T*2.0, True, False, ['all', 'nscand_only']),
    (DEFAULT_FAR_T*2.0, True, True, ['all', 'nscand_only', 'gps_only',
                                     'nscand_and_gps']),
    (DEFAULT_FAR_T/2.0, False, False, ['all', 'far_t_only']),
    (DEFAULT_FAR_T/2.0, False, True, ['all', 'far_t_only', 'gps_only',
                                      'far_t_and_gps']),
    (DEFAULT_FAR_T/2.0, True, False, ['all', 'far_t_only', 'nscand_only',
                                      'far_t_and_nscand']),
    (DEFAULT_FAR_T/2.0, True, True,
        ['all', 'far_t_only', 'nscand_only', 'gps_only', 'far_t_and_nscand',
         'far_t_and_gps', 'nscand_and_gps', 'far_t_and_nscand_and_gps']),
]

SUPEREVENT_UPDATE_ALERT_DATA = [
    # FAR = None and constant -------------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (None, None, False, False, None, []),
    (None, None, True, True, None, []),
    ### With labels -----------------------------------
    (None, None, False, False, DEFAULT_LABELS, []),
    (None, None, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, None, False, False, DEFAULT_LABEL_QUERY['labels'], []),
    (None, None, True, True, DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, None, False, True, None, ['nscand_only']),
    (None, None, True, False, None, []),
    ### With labels -----------------------------------
    (None, None, False, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (None, None, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, None, False, True, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (None, None, True, False, DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = above threshold and constant --------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, None, ['nscand_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True,
        DEFAULT_LABEL_QUERY['labels'], ['nscand_only',
                                        'nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = above threshold and increases -------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, None, ['nscand_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True,
        DEFAULT_LABEL_QUERY['labels'], ['nscand_only',
                                        'nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below threshold and constant --------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, None,
        ['nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True,
        DEFAULT_LABEL_QUERY['labels'], ['nscand_only', 'far_t_and_nscand',
                                        'nscand_and_labelq',
                                        'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below threshold and decreases -------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, None,
        ['nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True,
        DEFAULT_LABEL_QUERY['labels'], ['nscand_only', 'far_t_and_nscand',
                                        'nscand_and_labelq',
                                        'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below -> above threshold ------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, None,
        ['nscand_only']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = None -> above threshold -------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T*2, False, False, None, []),
    (None, DEFAULT_FAR_T*2, True, True, None, []),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T*2, False, False, DEFAULT_LABELS, []),
    (None, DEFAULT_FAR_T*2, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T*2, False, False, DEFAULT_LABEL_QUERY['labels'], []),
    (None, DEFAULT_FAR_T*2, True, True, DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T*2, False, True, None, ['nscand_only']),
    (None, DEFAULT_FAR_T*2, True, False, None, []),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T*2, False, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (None, DEFAULT_FAR_T*2, True, False, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T*2, False, True, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (None, DEFAULT_FAR_T*2, True, False, DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = None -> below threshold -------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T/2.0, False, False, None, ['far_t_only']),
    (None, DEFAULT_FAR_T/2.0, True, True, None,
        ['far_t_only', 'far_t_and_nscand']),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T/2.0, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (None, DEFAULT_FAR_T/2.0, True, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels']),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T/2.0, False, False, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, True, True, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq']),
    # FAR = None -> below threshold -------------------
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T/2.0, False, True, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand']),
    (None, DEFAULT_FAR_T/2.0, True, False, None, ['far_t_only']),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T/2.0, False, True, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labels', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (None, DEFAULT_FAR_T/2.0, True, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T/2.0, False, True, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labelq', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, True, False, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    # FAR = above -> below threshold ------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, None,
        ['far_t_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, None,
        ['far_t_only', 'far_t_and_nscand']),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels']),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq']),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, None,
        ['far_t_only']),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labels', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labelq', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
]

# Params: old_far,far,old_nscand,nscand,use_default_gps,labels,notif_descs
EVENT_UPDATE_ALERT_DATA = [
    # FAR = None and constant -------------------------
    ## No labels --------------------------------------
    ### NSCAND = constant -----------------------------
    (None, None, False, False, False, None, []),
    (None, None, False, False, True, None, []),
    (None, None, True, True, False, None, []),
    (None, None, True, True, True, None, []),
    ### With labels -----------------------------------
    (None, None, False, False, False, DEFAULT_LABELS, []),
    (None, None, False, False, True, DEFAULT_LABELS, []),
    (None, None, True, True, False, DEFAULT_LABELS, []),
    (None, None, True, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, None, False, False, False, DEFAULT_LABEL_QUERY['labels'], []),
    (None, None, False, False, True, DEFAULT_LABEL_QUERY['labels'], []),
    (None, None, True, True, False, DEFAULT_LABEL_QUERY['labels'], []),
    (None, None, True, True, True, DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, None, False, True, False, None, ['nscand_only']),
    (None, None, False, True, True, None, ['nscand_only', 'nscand_and_gps']),
    (None, None, True, False, False, None, []),
    (None, None, True, False, True, None, []),
    ### With labels -----------------------------------
    (None, None, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (None, None, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels', 'nscand_and_gps',
         'nscand_and_labels_and_gps']),
    (None, None, True, False, False, DEFAULT_LABELS, []),
    (None, None, True, False, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, None, False, True, False, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (None, None, False, True, True, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq', 'nscand_and_gps',
         'nscand_and_labelq_and_gps']),
    (None, None, True, False, False, DEFAULT_LABEL_QUERY['labels'], []),
    (None, None, True, False, True, DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = above threshold and constant --------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, True, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, True, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, False, None,
        ['nscand_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, True, None,
        ['nscand_only', 'nscand_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels', 'nscand_and_gps',
         'nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq', 'nscand_and_gps',
         'nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*2, True, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = above threshold and increases -------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, True, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, True, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, False, None,
        ['nscand_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, True, None,
        ['nscand_only', 'nscand_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, False, None, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels', 'nscand_and_gps',
         'nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, False, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq', 'nscand_and_gps',
         'nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T*4, True, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below threshold and constant --------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, True, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, True, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, False, None,
        ['nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, True, None,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_gps',
         'far_t_and_nscand_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels', 'nscand_and_gps',
         'far_t_and_nscand_and_gps', 'nscand_and_labels_and_gps', 
         'far_t_and_nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq', 'nscand_and_gps',
         'far_t_and_nscand_and_gps', 'nscand_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/2.0, True, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below threshold and decreases -------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, True, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, True, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, False, None,
        ['nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, True, None,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_gps',
         'far_t_and_nscand_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labels',
         'far_t_and_nscand_and_labels', 'nscand_and_gps',
         'far_t_and_nscand_and_gps', 'nscand_and_labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'far_t_and_nscand', 'nscand_and_labelq',
         'far_t_and_nscand_and_labelq', 'nscand_and_gps',
         'far_t_and_nscand_and_gps', 'nscand_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T/4.0, True, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = below -> above threshold ------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, True, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, True, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, True, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, False, None,
        ['nscand_only']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, True, None,
        ['nscand_only', 'nscand_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, False, None, []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, True, None, []),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels', 'nscand_and_gps',
         'nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, False, DEFAULT_LABELS,
        []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, True, DEFAULT_LABELS,
        []),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq', 'nscand_and_gps',
         'nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, False,
        DEFAULT_LABEL_QUERY['labels'], []),
    (DEFAULT_FAR_T/2.0, DEFAULT_FAR_T*2, True, False, True,
        DEFAULT_LABEL_QUERY['labels'], []),
    # FAR = None -> above threshold -------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T*2, False, False, False, None, []),
    (None, DEFAULT_FAR_T*2, False, False, True, None, []),
    (None, DEFAULT_FAR_T*2, True, True, False, None, []),
    (None, DEFAULT_FAR_T*2, True, True, True, None, []),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T*2, False, False, False, DEFAULT_LABELS, []),
    (None, DEFAULT_FAR_T*2, False, False, True, DEFAULT_LABELS, []),
    (None, DEFAULT_FAR_T*2, True, True, False, DEFAULT_LABELS, []),
    (None, DEFAULT_FAR_T*2, True, True, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T*2, False, False, False, DEFAULT_LABEL_QUERY['labels'],
        []),
    (None, DEFAULT_FAR_T*2, False, False, True, DEFAULT_LABEL_QUERY['labels'],
        []),
    (None, DEFAULT_FAR_T*2, True, True, False, DEFAULT_LABEL_QUERY['labels'],
        []),
    (None, DEFAULT_FAR_T*2, True, True, True, DEFAULT_LABEL_QUERY['labels'],
        []),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T*2, False, True, False, None, ['nscand_only']),
    (None, DEFAULT_FAR_T*2, False, True, True, None,
        ['nscand_only', 'nscand_and_gps']),
    (None, DEFAULT_FAR_T*2, True, False, False, None, []),
    (None, DEFAULT_FAR_T*2, True, False, True, None, []),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T*2, False, True, False, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels']),
    (None, DEFAULT_FAR_T*2, False, True, True, DEFAULT_LABELS,
        ['nscand_only', 'nscand_and_labels', 'nscand_and_gps',
         'nscand_and_labels_and_gps']),
    (None, DEFAULT_FAR_T*2, True, False, False, DEFAULT_LABELS, []),
    (None, DEFAULT_FAR_T*2, True, False, True, DEFAULT_LABELS, []),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T*2, False, True, False, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq']),
    (None, DEFAULT_FAR_T*2, False, True, True, DEFAULT_LABEL_QUERY['labels'],
        ['nscand_only', 'nscand_and_labelq', 'nscand_and_gps',
         'nscand_and_labelq_and_gps']),
    (None, DEFAULT_FAR_T*2, True, False, False, DEFAULT_LABEL_QUERY['labels'],
        []),
    (None, DEFAULT_FAR_T*2, True, False, True, DEFAULT_LABEL_QUERY['labels'],
        []),
    # FAR = None -> below threshold -------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T/2.0, False, False, False, None, ['far_t_only']),
    (None, DEFAULT_FAR_T/2.0, False, False, True, None,
        ['far_t_only', 'far_t_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, True, False, None,
        ['far_t_only', 'far_t_and_nscand']),
    (None, DEFAULT_FAR_T/2.0, True, True, True, None,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_gps',
         'far_t_and_nscand_and_gps']),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T/2.0, False, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (None, DEFAULT_FAR_T/2.0, False, False, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels', 'far_t_and_gps',
         'far_t_and_labels_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, True, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels']),
    (None, DEFAULT_FAR_T/2.0, True, True, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels', 'far_t_and_gps',
         'far_t_and_nscand_and_gps', 'far_t_and_labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T/2.0, False, False, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, False, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq', 'far_t_and_gps',
         'far_t_and_labelq_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, True, False, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, True, True, True, DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq', 'far_t_and_gps',
         'far_t_and_nscand_and_gps', 'far_t_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    # FAR = None -> below threshold -------------------
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (None, DEFAULT_FAR_T/2.0, False, True, False, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand']),
    (None, DEFAULT_FAR_T/2.0, False, True, True, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_gps',
         'nscand_and_gps', 'far_t_and_nscand_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, False, False, None, ['far_t_only']),
    (None, DEFAULT_FAR_T/2.0, True, False, True, None,
        ['far_t_only', 'far_t_and_gps']),
    ### With labels -----------------------------------
    (None, DEFAULT_FAR_T/2.0, False, True, False, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labels', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (None, DEFAULT_FAR_T/2.0, False, True, True, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labels', 'nscand_and_labels',
         'far_t_and_nscand_and_labels', 'far_t_and_gps', 'nscand_and_gps',
         'far_t_and_nscand_and_gps', 'far_t_and_labels_and_gps',
         'nscand_and_labels_and_gps', 'far_t_and_nscand_and_labels_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (None, DEFAULT_FAR_T/2.0, True, False, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels', 'far_t_and_gps',
         'far_t_and_labels_and_gps']),
    ### With labels matching label query --------------
    (None, DEFAULT_FAR_T/2.0, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'nscand_and_labelq', 'far_t_and_nscand_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'nscand_and_labelq', 'far_t_and_nscand_and_labelq',
         'far_t_and_gps', 'nscand_and_gps', 'far_t_and_nscand_and_gps',
         'far_t_and_labelq_and_gps', 'nscand_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    (None, DEFAULT_FAR_T/2.0, True, False, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (None, DEFAULT_FAR_T/2.0, True, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq', 'far_t_and_gps',
         'far_t_and_labelq_and_gps']),
    # FAR = above -> below threshold ------------------
    ## NSCAND = constant ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, False, None,
        ['far_t_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, True, None,
        ['far_t_only', 'far_t_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, False, None,
        ['far_t_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, True, None,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_gps',
         'far_t_and_nscand_and_gps']),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels', 'far_t_and_gps',
         'far_t_and_labels_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labels',
         'far_t_and_nscand_and_labels', 'far_t_and_gps',
         'far_t_and_nscand_and_gps', 'far_t_and_labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq', 'far_t_and_gps',
         'far_t_and_labelq_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'far_t_and_nscand_and_labelq', 'far_t_and_gps',
         'far_t_and_nscand_and_gps', 'far_t_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    ## NSCAND = changing ------------------------------
    ### No labels -------------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, False, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, True, None,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_gps', 'nscand_and_gps', 'far_t_and_nscand_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, False, None,
        ['far_t_only']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, True, None,
        ['far_t_only', 'far_t_and_gps']),
    ### With labels -----------------------------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, False, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand',
         'far_t_and_labels', 'nscand_and_labels',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, True, DEFAULT_LABELS,
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_labels',
         'nscand_and_labels', 'far_t_and_nscand_and_labels', 'far_t_and_gps',
         'nscand_and_gps', 'far_t_and_nscand_and_gps',
         'far_t_and_labels_and_gps', 'nscand_and_labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, False, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, True, DEFAULT_LABELS,
        ['far_t_only', 'far_t_and_labels', 'far_t_and_gps',
         'far_t_and_labels_and_gps']),
    ### With labels matching label query --------------
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'nscand_and_labelq', 'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, False, True, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'nscand_only', 'far_t_and_nscand', 'far_t_and_labelq',
         'nscand_and_labelq', 'far_t_and_nscand_and_labelq', 'far_t_and_gps',
         'nscand_and_gps', 'far_t_and_nscand_and_gps',
         'far_t_and_labelq_and_gps', 'nscand_and_labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, False,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq']),
    (DEFAULT_FAR_T*2, DEFAULT_FAR_T/2.0, True, False, True,
        DEFAULT_LABEL_QUERY['labels'],
        ['far_t_only', 'far_t_and_labelq', 'far_t_and_gps',
         'far_t_and_labelq_and_gps']),
]

SUPEREVENT_LABEL_ADDED_ALERT_DATA = [
    # Label criteria not met --------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], None, []),
    (None, True, DEFAULT_LABELS[0], None, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], None, []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], None, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], None, []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], None, []),
    # Label criteria met ------------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['labels_only']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['nscand_and_labels', 'labels_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['labels_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['nscand_and_labels', 'labels_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['far_t_and_labels', 'labels_only']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:],
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels']),
    # Label criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        ['labels_only']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        ['nscand_and_labels', 'labels_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], ['labels_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        ['nscand_and_labels', 'labels_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        ['far_t_and_labels', 'labels_only']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels']),
    # Label criteria previously met -------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, DEFAULT_LABELS, []),
    (None, True, RANDOM_LABEL, DEFAULT_LABELS, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABELS, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABELS, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABELS, []),
    # Label query criteria not met --------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, []),
    # Label query criteria met -------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], ['labelq_only']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:],
        ['nscand_and_labelq', 'labelq_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], ['labelq_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:],
        ['nscand_and_labelq', 'labelq_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:],
        ['far_t_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:],
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq']),
    # Label query criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['labelq_only']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['nscand_and_labelq', 'labelq_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['labelq_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['nscand_and_labelq', 'labelq_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['far_t_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL],
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq']),
    # Label query criteria previously met -------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], []),
    (None, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], []),
]

# Params: far,nscand,new_label,old_labels,use_default_gps,notif_descs
EVENT_LABEL_ADDED_ALERT_DATA = [
    # Label criteria not met --------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], None, False, []),
    (None, False, DEFAULT_LABELS[0], None, True, []),
    (None, True, DEFAULT_LABELS[0], None, False, []),
    (None, True, DEFAULT_LABELS[0], None, True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], None, False, []),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], None, True, []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], None, False, []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], None, True, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], None, False, []),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], None, True, []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], None, False, []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], None, True, []),
    # Label criteria met ------------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['labels_only']),
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['labels_only', 'labels_and_gps']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['nscand_and_labels', 'labels_only']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['nscand_and_labels', 'labels_only', 'nscand_and_labels_and_gps',
         'labels_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['labels_only']),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['labels_only', 'labels_and_gps']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['nscand_and_labels', 'labels_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['nscand_and_labels', 'labels_only', 'nscand_and_labels_and_gps',
         'labels_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['far_t_and_labels', 'labels_only']),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['far_t_and_labels', 'labels_only', 'far_t_and_labels_and_gps',
         'labels_and_gps']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], False,
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:], True,
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels', 'far_t_and_labels_and_gps',
         'nscand_and_labels_and_gps', 'labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    # Label criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        False, ['labels_only']),
    (None, False, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        True, ['labels_only', 'labels_and_gps']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        False, ['nscand_and_labels', 'labels_only']),
    (None, True, DEFAULT_LABELS[0], DEFAULT_LABELS[1:] + [RANDOM_LABEL],
        True, ['nscand_and_labels', 'labels_only', 'labels_and_gps',
               'nscand_and_labels_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], False, ['labels_only']),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], True,
        ['labels_only', 'labels_and_gps']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], False,
        ['nscand_and_labels', 'labels_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], True,
        ['nscand_and_labels', 'labels_only', 'labels_and_gps',
         'nscand_and_labels_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], False,
        ['far_t_and_labels', 'labels_only']),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], True,
        ['far_t_and_labels', 'labels_only', 'labels_and_gps',
         'far_t_and_labels_and_gps']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], False,
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABELS[0],
        DEFAULT_LABELS[1:] + [RANDOM_LABEL], True,
        ['far_t_and_labels', 'nscand_and_labels', 'labels_only',
         'far_t_and_nscand_and_labels', 'far_t_and_labels_and_gps',
         'nscand_and_labels_and_gps', 'labels_and_gps',
         'far_t_and_nscand_and_labels_and_gps']),
    # Label criteria previously met -------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (None, False, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    (None, True, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (None, True, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABELS, False, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABELS, True, []),
    # Label query criteria not met --------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0], None, False, []),
    (None, False, DEFAULT_LABEL_QUERY['labels'][0], None, True, []),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0], None, False, []),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0], None, True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, False,
        []),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, True,
        []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, False,
        []),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, True,
        []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, False,
        []),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0], None, True,
        []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, False,
        []),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0], None, True,
        []),
    # Label query criteria met -------------------------
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False, ['labelq_only']),
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['labelq_only', 'labelq_and_gps']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False,
        ['nscand_and_labelq', 'labelq_only']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['nscand_and_labelq', 'labelq_only', 'labelq_and_gps',
         'nscand_and_labelq_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False, ['labelq_only']),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['labelq_only', 'labelq_and_gps']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False,
        ['nscand_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['nscand_and_labelq', 'labelq_only', 'labelq_and_gps',
         'nscand_and_labelq_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False,
        ['far_t_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['far_t_and_labelq', 'labelq_only', 'labelq_and_gps',
         'far_t_and_labelq_and_gps']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], False,
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:], True,
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq', 'far_t_and_labelq_and_gps',
         'nscand_and_labelq_and_gps', 'labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    # Label query criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['labelq_only']),
    (None, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['labelq_only', 'labelq_and_gps']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['nscand_and_labelq', 'labelq_only']),
    (None, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['nscand_and_labelq', 'labelq_only', 'labelq_and_gps',
         'nscand_and_labelq_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['labelq_only']),
    (DEFAULT_FAR_T*2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['labelq_only', 'labelq_and_gps']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['nscand_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T*2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['nscand_and_labelq', 'labelq_only', 'labelq_and_gps',
         'nscand_and_labelq_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['far_t_and_labelq', 'labelq_only']),
    (DEFAULT_FAR_T/2.0, False, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['far_t_and_labelq', 'labelq_only', 'labelq_and_gps',
         'far_t_and_labelq_and_gps']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], False,
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq']),
    (DEFAULT_FAR_T/2.0, True, DEFAULT_LABEL_QUERY['labels'][0],
        DEFAULT_LABEL_QUERY['labels'][1:] + [RANDOM_LABEL], True,
        ['far_t_and_labelq', 'nscand_and_labelq', 'labelq_only',
         'far_t_and_nscand_and_labelq', 'far_t_and_labelq_and_gps',
         'nscand_and_labelq_and_gps', 'labelq_and_gps',
         'far_t_and_nscand_and_labelq_and_gps']),
    # Label query criteria previously met -------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], False, []),
    (None, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], True, []),
    (None, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], False, []),
    (None, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'], True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        False, []),
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        True, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        False, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        True, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        False, []),
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        True, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        False, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, DEFAULT_LABEL_QUERY['labels'],
        True, []),
]

SUPEREVENT_LABEL_REMOVED_ALERT_DATA = [
    # Label criteria not met --------------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, None, []),
    (None, True, RANDOM_LABEL, None, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, None, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, None, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, None, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, None, []),
    # Label criteria met ------------------------------
    ## FAR = None -------------------------------------
    (None, False, 'L7', ['L5', 'L6'], ['labelq2_only']),
    (None, True, 'L7', ['L5', 'L6'],
        ['nscand_and_labelq2', 'labelq2_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6'],
        ['labelq2_only']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6'],
        ['nscand_and_labelq2', 'labelq2_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6'],
        ['far_t_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6'],
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2']),
    # Label criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['labelq2_only']),
    (None, True, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['nscand_and_labelq2', 'labelq2_only']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['labelq2_only']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['nscand_and_labelq2', 'labelq2_only']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['far_t_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL],
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2']),
    # Label criteria previously met -------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, ['L5', 'L6'], []),
    (None, True, RANDOM_LABEL, ['L5', 'L6'], []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, ['L5', 'L6'], []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, ['L5', 'L6'], []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, ['L5', 'L6'], []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, ['L5', 'L6'], []),
]

# Params: far,nscand,removed_label,labels,use_default_gps,notif_descs
EVENT_LABEL_REMOVED_ALERT_DATA = [
    # Label criteria not met --------------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, None, False, []),
    (None, False, RANDOM_LABEL, None, True, []),
    (None, True, RANDOM_LABEL, None, False, []),
    (None, True, RANDOM_LABEL, None, True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, None, False, []),
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, None, True, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, None, False, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, None, True, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, None, False, []),
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, None, True, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, None, False, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, None, True, []),
    # Label criteria met ------------------------------
    ## FAR = None -------------------------------------
    (None, False, 'L7', ['L5', 'L6'], False, ['labelq2_only']),
    (None, False, 'L7', ['L5', 'L6'], True,
        ['labelq2_only', 'labelq2_and_gps']),
    (None, True, 'L7', ['L5', 'L6'], False,
        ['nscand_and_labelq2', 'labelq2_only']),
    (None, True, 'L7', ['L5', 'L6'], True,
        ['nscand_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'nscand_and_labelq2_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6'], False,
        ['labelq2_only']),
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6'], True,
        ['labelq2_only', 'labelq2_and_gps']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6'], False,
        ['nscand_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6'], True,
        ['nscand_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'nscand_and_labelq2_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6'], False,
        ['far_t_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6'], True,
        ['far_t_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'far_t_and_labelq2_and_gps']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6'], False,
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6'], True,
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2', 'labelq2_and_gps',
         'far_t_and_labelq2_and_gps', 'nscand_and_labelq2_and_gps',
         'far_t_and_nscand_and_labelq2_and_gps']),
    # Label criteria met, some additional labels previously added
    ## FAR = None -------------------------------------
    (None, False, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['labelq2_only']),
    (None, False, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['labelq2_only', 'labelq2_and_gps',]),
    (None, True, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['nscand_and_labelq2', 'labelq2_only']),
    (None, True, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['nscand_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'nscand_and_labelq2_and_gps']),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['labelq2_only']),
    (DEFAULT_FAR_T*2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['labelq2_only', 'labelq2_and_gps']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['nscand_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T*2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['nscand_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'nscand_and_labelq2_and_gps']),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['far_t_and_labelq2', 'labelq2_only']),
    (DEFAULT_FAR_T/2.0, False, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['far_t_and_labelq2', 'labelq2_only', 'labelq2_and_gps',
         'far_t_and_labelq2_and_gps']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL], False,
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2']),
    (DEFAULT_FAR_T/2.0, True, 'L7', ['L5', 'L6', RANDOM_LABEL], True,
        ['far_t_and_labelq2', 'nscand_and_labelq2', 'labelq2_only',
         'far_t_and_nscand_and_labelq2', 'labelq2_and_gps',
         'far_t_and_labelq2_and_gps', 'nscand_and_labelq2_and_gps',
         'far_t_and_nscand_and_labelq2_and_gps']),
    # Label criteria previously met -------------------
    ## FAR = None -------------------------------------
    (None, False, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (None, False, RANDOM_LABEL, ['L5', 'L6'], True, []),
    (None, True, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (None, True, RANDOM_LABEL, ['L5', 'L6'], True, []),
    ## FAR > threshold --------------------------------
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (DEFAULT_FAR_T*2.0, False, RANDOM_LABEL, ['L5', 'L6'], True, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (DEFAULT_FAR_T*2.0, True, RANDOM_LABEL, ['L5', 'L6'], True, []),
    ## FAR < threshold --------------------------------
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (DEFAULT_FAR_T/2.0, False, RANDOM_LABEL, ['L5', 'L6'], True, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, ['L5', 'L6'], False, []),
    (DEFAULT_FAR_T/2.0, True, RANDOM_LABEL, ['L5', 'L6'], True, []),
]


###############################################################################
# TESTS #######################################################################
###############################################################################
# Superevent tests ------------------------------------------------------------
@pytest.mark.parametrize("far,nscand,notif_descs",
                         SUPEREVENT_CREATION_ALERT_DATA)
@pytest.mark.django_db
def test_superevent_creation_alerts(
    superevent, superevent_notifications,
    far, nscand, notif_descs,
):

    # Set up superevent state
    superevent.preferred_event.far = far
    superevent.preferred_event.is_ns_candidate = \
        types.MethodType(lambda self: nscand, superevent.preferred_event)

    # Set up recipient getter
    recipient_getter = CreationRecipientGetter(superevent)
    recipient_getter.queryset = superevent_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()
    assert matched_notifications.count() == len(notif_descs)


@pytest.mark.parametrize("old_far,far,old_nscand,nscand,labels,notif_descs",
                         SUPEREVENT_UPDATE_ALERT_DATA)
@pytest.mark.django_db
def test_superevent_update_alerts(
    superevent, superevent_notifications,
    old_far, far, old_nscand, nscand, labels, notif_descs,
):

    # Set up superevent state
    superevent.preferred_event.far = far
    superevent.preferred_event.is_ns_candidate = \
        types.MethodType(lambda self: nscand, superevent.preferred_event)
    if labels is not None:
        for label_name in labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            superevent.labelling_set.create(label=label,
                                            creator=superevent.submitter)

    # Set up recipient getter
    recipient_getter = UpdateRecipientGetter(superevent, old_far=old_far,
                                             old_nscand=old_nscand)
    recipient_getter.queryset = superevent_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


@pytest.mark.parametrize("far,nscand,new_label,old_labels,notif_descs",
                         SUPEREVENT_LABEL_ADDED_ALERT_DATA)
@pytest.mark.django_db
def test_superevent_label_added_alerts(
    superevent, superevent_notifications,
    far, nscand, new_label, old_labels, notif_descs,
):

    # Set up superevent state
    superevent.preferred_event.far = far
    superevent.preferred_event.is_ns_candidate = \
        types.MethodType(lambda self: nscand, superevent.preferred_event)
    if old_labels is not None:
        for label_name in old_labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            superevent.labelling_set.create(label=label,
                                            creator=superevent.submitter)
    # Add new label
    label_obj, _ = Label.objects.get_or_create(name=new_label)
    superevent.labelling_set.create(label=label_obj,
                                    creator=superevent.submitter)

    # Set up recipient getter
    recipient_getter = LabelAddedRecipientGetter(superevent, label=label_obj)
    recipient_getter.queryset = superevent_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


@pytest.mark.parametrize("far,nscand,removed_label,labels,notif_descs",
                         SUPEREVENT_LABEL_REMOVED_ALERT_DATA)
@pytest.mark.django_db
def test_superevent_label_removed_alerts(
    superevent, superevent_notifications,
    far, nscand, removed_label, labels, notif_descs,
):
    # NOTE: labels being removed should never result in alerts for
    # notifications which specify a label criteria (instead of a label query)

    # Set up superevent state
    superevent.preferred_event.far = far
    superevent.preferred_event.is_ns_candidate = \
        types.MethodType(lambda self: nscand, superevent.preferred_event)
    if labels is not None:
        for label_name in labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            superevent.labelling_set.create(label=label,
                                            creator=superevent.submitter)

    # Add new label
    label_obj, _ = Label.objects.get_or_create(name=removed_label)

    # Set up recipient getter
    recipient_getter = LabelRemovedRecipientGetter(superevent, label=label_obj)
    recipient_getter.queryset = superevent_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


# Event tests -----------------------------------------------------------------
@pytest.mark.parametrize("far,nscand,use_default_gps,notif_descs",
                         EVENT_CREATION_ALERT_DATA)
@pytest.mark.django_db
def test_event_creation_alerts(
    event, event_notifications, far, nscand, use_default_gps, notif_descs,
):

    # Set up event state
    event.far = far
    event.is_ns_candidate = types.MethodType(lambda self: nscand, event)
    if use_default_gps:
        event.group = Group.objects.get(name=DEFAULT_GROUP)
        event.pipeline = Pipeline.objects.get(name=DEFAULT_PIPELINE)
        event.search = Search.objects.get(name=DEFAULT_SEARCH)
        event.save()

    # Set up recipient getter
    recipient_getter = CreationRecipientGetter(event)
    recipient_getter.queryset = event_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()
    assert matched_notifications.count() == len(notif_descs)


@pytest.mark.parametrize(
    "old_far,far,old_nscand,nscand,use_default_gps,labels,notif_descs",
    EVENT_UPDATE_ALERT_DATA
)
@pytest.mark.django_db
def test_event_update_alerts(
    event, event_notifications, old_far, far, old_nscand, nscand,
    use_default_gps, labels, notif_descs,
):
    # Set up event state
    event.far = far
    event.is_ns_candidate = types.MethodType(lambda self: nscand, event)
    if use_default_gps:
        event.group = Group.objects.get(name=DEFAULT_GROUP)
        event.pipeline = Pipeline.objects.get(name=DEFAULT_PIPELINE)
        event.search = Search.objects.get(name=DEFAULT_SEARCH)
        event.save()
    if labels is not None:
        for label_name in labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            event.labelling_set.create(label=label, creator=event.submitter)

    # Set up recipient getter
    recipient_getter = UpdateRecipientGetter(event, old_far=old_far,
                                             old_nscand=old_nscand)
    recipient_getter.queryset = event_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


@pytest.mark.parametrize(
    "far,nscand,new_label,old_labels,use_default_gps,notif_descs",
    EVENT_LABEL_ADDED_ALERT_DATA
)
@pytest.mark.django_db
def test_event_label_added_alerts(
    event, event_notifications, far, nscand, new_label, old_labels,
    use_default_gps, notif_descs,
):
    # Set up event state
    event.far = far
    event.is_ns_candidate = types.MethodType(lambda self: nscand, event)
    if use_default_gps:
        event.group = Group.objects.get(name=DEFAULT_GROUP)
        event.pipeline = Pipeline.objects.get(name=DEFAULT_PIPELINE)
        event.search = Search.objects.get(name=DEFAULT_SEARCH)
        event.save()
    if old_labels is not None:
        for label_name in old_labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            event.labelling_set.create(label=label, creator=event.submitter)

    # Add new label
    label_obj, _ = Label.objects.get_or_create(name=new_label)
    event.labelling_set.create(label=label_obj, creator=event.submitter)

    # Set up recipient getter
    recipient_getter = LabelAddedRecipientGetter(event, label=label_obj)
    recipient_getter.queryset = event_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


@pytest.mark.parametrize(
    "far,nscand,removed_label,labels,use_default_gps,notif_descs",
    EVENT_LABEL_REMOVED_ALERT_DATA
)
@pytest.mark.django_db
def test_event_label_removed_alerts(
    event, event_notifications, far, nscand, removed_label, labels,
    use_default_gps, notif_descs,
):
    # Set up event state
    event.far = far
    event.is_ns_candidate = types.MethodType(lambda self: nscand, event)
    if use_default_gps:
        event.group = Group.objects.get(name=DEFAULT_GROUP)
        event.pipeline = Pipeline.objects.get(name=DEFAULT_PIPELINE)
        event.search = Search.objects.get(name=DEFAULT_SEARCH)
        event.save()
    if labels is not None:
        for label_name in labels:
            label, _ = Label.objects.get_or_create(name=label_name)
            event.labelling_set.create(label=label, creator=event.submitter)

    # Add new label
    label_obj, _ = Label.objects.get_or_create(name=removed_label)

    # Set up recipient getter
    recipient_getter = LabelRemovedRecipientGetter(event, label=label_obj)
    recipient_getter.queryset = event_notifications

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()

    # Test results
    assert matched_notifications.count() == len(notif_descs)
    for desc in notif_descs:
        assert matched_notifications.filter(description=desc).exists()


# Other tests -----------------------------------------------------------------
@pytest.mark.django_db
def test_complex_label_query(superevent):
    # NOTE: L1 & ~L2 | L3 == L1 & (~L2 | L3)
    n = Notification.objects.create(
        label_query='L1 & ~L2 | L3',
        user=superevent.submitter,
        description='test notification'
    )

    # Set up superevent labels
    for label_name in ['L1', 'L2', 'L3']:
        l, _ = Label.objects.get_or_create(name=label_name)
        n.labels.add(l)

    # Test label added recipients for L1 being added
    l1 = Label.objects.get(name='L1')
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l1)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 1
    assert matched_notifications.first().description == n.description

    # Test label added recipients for L3 being added (L1 already added)
    l3 = Label.objects.get(name='L3')
    superevent.labelling_set.create(creator=superevent.submitter, label=l3)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l3)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 1
    assert matched_notifications.first().description == n.description

    # Test label added recipients for L3 being added (no L1)
    l3 = Label.objects.get(name='L3')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l3)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l3)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 0

    # Test label added recipients for L1 being added (with L2)
    l1 = Label.objects.get(name='L1')
    l2 = Label.objects.get(name='L2')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l2)
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l1)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 0

    # Test label added recipients for L3 being added (with L1 and L2)
    l1 = Label.objects.get(name='L1')
    l2 = Label.objects.get(name='L2')
    l3 = Label.objects.get(name='L3')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    superevent.labelling_set.create(creator=superevent.submitter, label=l2)
    superevent.labelling_set.create(creator=superevent.submitter, label=l3)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l3)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 1
    assert matched_notifications.first().description == n.description

    # Test label removed recipients for L2 being removed (with L1)
    l1 = Label.objects.get(name='L1')
    l2 = Label.objects.get(name='L2')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    recipient_getter = LabelRemovedRecipientGetter(superevent, label=l2)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 1
    assert matched_notifications.first().description == n.description

    # Test label removed recipients for L3 being removed (with L1)
    l1 = Label.objects.get(name='L1')
    l3 = Label.objects.get(name='L3')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    recipient_getter = LabelRemovedRecipientGetter(superevent, label=l3)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 1
    assert matched_notifications.first().description == n.description

    # Test label removed recipients for L2 being removed (with L1 and L3)
    l1 = Label.objects.get(name='L1')
    l2 = Label.objects.get(name='L2')
    l3 = Label.objects.get(name='L3')
    superevent.labels.clear()
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    superevent.labelling_set.create(creator=superevent.submitter, label=l3)
    recipient_getter = LabelAddedRecipientGetter(superevent, label=l2)
    matched_notifications = recipient_getter.get_notifications()
    # TODO: this shouldn't match, since it was already triggered on the
    # previous state, where L1, L2, and L3 were all applied (but it does)
    #assert matched_notifications.count() == 0


@pytest.mark.django_db
def test_label_removal_with_only_labels_list(superevent):
    n = Notification.objects.create(
        user=superevent.submitter,
        description='test notification'
    )

    # Set up superevent labels
    for label_name in ['L1', 'L2']:
        l, _ = Label.objects.get_or_create(name=label_name)
        n.labels.add(l)

    # Test label added recipients for L1 being added
    l1 = Label.objects.get(name='L1')
    l2 = Label.objects.get(name='L2')
    l3, _ = Label.objects.get_or_create(name='L3')
    superevent.labelling_set.create(creator=superevent.submitter, label=l1)
    superevent.labelling_set.create(creator=superevent.submitter, label=l2)
    recipient_getter = LabelRemovedRecipientGetter(superevent, label=l3)
    matched_notifications = recipient_getter.get_notifications()
    assert matched_notifications.count() == 0


@pytest.mark.parametrize("old_far,new_far,far_t,match",
                         [(1, 0.5, 0.5, False), (0.5, 0.25, 0.5, True)])
@pytest.mark.django_db
def test_update_alert_far_threshold_edge(superevent, old_far, new_far, far_t,
                                         match):
    n = Notification.objects.create(
        user=superevent.submitter,
        far_threshold=far_t,
        description='test notification'
    )

    # Set up superevent state
    superevent.preferred_event.far = new_far

    # Set up recipient getter
    recipient_getter = UpdateRecipientGetter(superevent, old_far=old_far,
                                             old_nscand=False)

    # Get notifications
    matched_notifications = recipient_getter.get_notifications()
    if match:
        assert matched_notifications.count() == 1
        assert matched_notifications.first().description == n.description
    else:
        assert matched_notifications.count() == 0
