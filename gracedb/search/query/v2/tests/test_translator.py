"""
Tests for the v2 query translator.

Tests in this file are unit tests for the translate() function.  They compare
Q objects directly (Django Q supports equality comparison) and inspect the
needs_distinct return value.

Label conditions are tested structurally (checking for Exists instances) using
the real production models.  No database access is required for label tests —
model metadata and lazy QuerySet construction work without hitting the DB.

Tests that require database access (e.g., creating real Event objects to
verify queryset filtering end-to-end) are marked with @pytest.mark.django_db.
"""
from functools import reduce

import pytest
from django.db.models import Exists, Q

from search.query.v2.translator import (
    translate,
    inject_default_filter,
    build_default_filter,
)
from search.query.v2.validator import QueryValidationError, validate
from search.constants import RUN_MAP_FLAT

from events.models import Event
from superevents.models import Superevent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def t(node, object_type='event', model_class=None):
    """Shorthand: translate and return (Q, distinct)."""
    return translate(node, object_type, model_class)


def q_only(node, object_type='event', model_class=None):
    """Translate and return only the Q object."""
    q, _ = translate(node, object_type, model_class)
    return q


def label_t(node, object_type='event'):
    """Translate a tree that contains label conditions."""
    mc = Event if object_type == 'event' else Superevent
    return translate(node, object_type, mc)


def label_q(node, object_type='event'):
    q, _ = label_t(node, object_type)
    return q


# ---------------------------------------------------------------------------
# Leaf: numeric fields
# ---------------------------------------------------------------------------

def test_far_lt_event():
    q, nd = t({'field': 'far', 'op': '<', 'value': 1e-5})
    assert q == Q(far__lt=1e-5)
    assert nd is False


def test_far_lte():
    assert q_only({'field': 'far', 'op': '<=', 'value': 1e-5}) == Q(far__lte=1e-5)


def test_far_gte():
    assert q_only({'field': 'far', 'op': '>=', 'value': 1e-7}) == Q(far__gte=1e-7)


def test_far_eq():
    assert q_only({'field': 'far', 'op': '=', 'value': 1e-5}) == Q(far=1e-5)


def test_far_neq():
    assert q_only({'field': 'far', 'op': '!=', 'value': 1e-5}) == ~Q(far=1e-5)


def test_far_between():
    assert q_only({'field': 'far', 'op': 'between', 'value': [1e-8, 1e-4]}) == Q(far__range=[1e-8, 1e-4])


def test_far_is_null_true():
    assert q_only({'field': 'far', 'op': 'is_null', 'value': True}) == Q(far__isnull=True)


def test_far_is_null_false():
    assert q_only({'field': 'far', 'op': 'is_null', 'value': False}) == Q(far__isnull=False)


def test_gpstime_between():
    q, _ = t({'field': 'gpstime', 'op': 'between', 'value': [1187008882.0, 1187008900.0]})
    assert q == Q(gpstime__range=[1187008882.0, 1187008900.0])


def test_nevents():
    assert q_only({'field': 'nevents', 'op': '=', 'value': 2}) == Q(nevents=2)


# ---------------------------------------------------------------------------
# Leaf: string fields
# ---------------------------------------------------------------------------

def test_instruments_contains():
    assert q_only({'field': 'instruments', 'op': 'contains', 'value': 'L1'}) == Q(instruments__icontains='L1')


def test_instruments_eq():
    assert q_only({'field': 'instruments', 'op': '=', 'value': 'H1,L1'}) == Q(instruments='H1,L1')


def test_instruments_alias_ifos():
    assert q_only({'field': 'ifos', 'op': 'contains', 'value': 'H1'}) == Q(instruments__icontains='H1')


# ---------------------------------------------------------------------------
# Leaf: db_enum fields (case-insensitive)
# ---------------------------------------------------------------------------

def test_group_eq_iexact():
    assert q_only({'field': 'group', 'op': '=', 'value': 'CBC'}) == Q(group__name__iexact='CBC')


def test_group_eq_lowercase():
    assert q_only({'field': 'group', 'op': '=', 'value': 'cbc'}) == Q(group__name__iexact='cbc')


def test_pipeline_contains():
    assert q_only({'field': 'pipeline', 'op': 'contains', 'value': 'lal'}) == Q(pipeline__name__icontains='lal')


def test_pipeline_in():
    q, _ = t({'field': 'pipeline', 'op': 'in', 'value': ['gstlal', 'pycbc']})
    expected = Q(pipeline__name__iexact='gstlal') | Q(pipeline__name__iexact='pycbc')
    assert q == expected


def test_search_is_null():
    # search is_null uses the special isnull_orm_path 'search__isnull'
    assert q_only({'field': 'search', 'op': 'is_null', 'value': True}) == Q(search__isnull=True)


# ---------------------------------------------------------------------------
# Leaf: graceid fields
# ---------------------------------------------------------------------------

def test_event_id_eq():
    assert q_only({'field': 'id', 'op': '=', 'value': 'G123456'}) == Q(graceid__iexact='G123456')


def test_event_id_startswith():
    assert q_only({'field': 'id', 'op': 'startswith', 'value': 'G12'}) == Q(graceid__istartswith='G12')


def test_event_id_alias_graceid():
    assert q_only({'field': 'graceid', 'op': '=', 'value': 'T1234'}) == Q(graceid__iexact='T1234')


def test_event_id_in():
    q, _ = t({'field': 'id', 'op': 'in', 'value': ['G100', 'G200']})
    expected = Q(graceid__iexact='G100') | Q(graceid__iexact='G200')
    assert q == expected


# ---------------------------------------------------------------------------
# Leaf: boolean derived fields
# ---------------------------------------------------------------------------

def test_in_superevent_true():
    assert q_only({'field': 'in_superevent', 'op': '=', 'value': True}) == Q(superevent__isnull=False)


def test_in_superevent_false():
    assert q_only({'field': 'in_superevent', 'op': '=', 'value': False}) == Q(superevent__isnull=True)


def test_is_preferred_event_true():
    assert q_only({'field': 'is_preferred_event', 'op': '=', 'value': True}) == Q(superevent_preferred_for__isnull=False)


def test_is_preferred_event_false():
    assert q_only({'field': 'is_preferred_event', 'op': '=', 'value': False}) == Q(superevent_preferred_for__isnull=True)


# ---------------------------------------------------------------------------
# Leaf: submitter
# ---------------------------------------------------------------------------

def test_submitter_contains():
    q, _ = t({'field': 'submitter', 'op': 'contains', 'value': 'einstein'})
    expected = Q(submitter__username__icontains='einstein') | Q(submitter__last_name__icontains='einstein')
    assert q == expected


# ---------------------------------------------------------------------------
# Leaf: runid (virtual field)
# ---------------------------------------------------------------------------

def test_runid_single_range_event():
    q, _ = t({'field': 'runid', 'op': '=', 'value': 'O3'})
    expected = Q(gpstime__range=RUN_MAP_FLAT['O3'][0])
    assert q == expected


def test_runid_multi_range_event():
    q, _ = t({'field': 'runid', 'op': '=', 'value': 'O4'})
    expected = reduce(Q.__or__, [Q(gpstime__range=tup) for tup in RUN_MAP_FLAT['O4']], Q())
    assert q == expected


def test_runid_superevent():
    q, _ = t({'field': 'runid', 'op': '=', 'value': 'O3'}, object_type='superevent')
    expected = Q(t_0__range=RUN_MAP_FLAT['O3'][0])
    assert q == expected


def test_runid_superevent_alias_gpstime():
    # 'gpstime' is an alias for 't_0' on superevents
    q, _ = t({'field': 'gpstime', 'op': '>', 'value': 1234567890.0}, object_type='superevent')
    assert q == Q(t_0__gt=1234567890.0)


# ---------------------------------------------------------------------------
# Leaf: superevent fields
# ---------------------------------------------------------------------------

def test_superevent_t0_between():
    q, _ = t({'field': 't_0', 'op': 'between', 'value': [1234.0, 5678.0]}, 'superevent')
    assert q == Q(t_0__range=[1234.0, 5678.0])


def test_superevent_category_eq():
    assert q_only({'field': 'category', 'op': '=', 'value': 'Production'}, 'superevent') == Q(category='P')


def test_superevent_category_test():
    assert q_only({'field': 'category', 'op': '=', 'value': 'Test'}, 'superevent') == Q(category='T')


def test_superevent_category_mdc():
    assert q_only({'field': 'category', 'op': '=', 'value': 'MDC'}, 'superevent') == Q(category='M')


def test_superevent_category_neq():
    assert q_only({'field': 'category', 'op': '!=', 'value': 'Test'}, 'superevent') == ~Q(category='T')


def test_superevent_category_in():
    q, _ = t({'field': 'category', 'op': 'in', 'value': ['Test', 'MDC']}, 'superevent')
    assert q == Q(category__in=['T', 'M'])


def test_superevent_is_gw():
    assert q_only({'field': 'is_gw', 'op': '=', 'value': True}, 'superevent') == Q(is_gw=True)


def test_superevent_is_exposed():
    assert q_only({'field': 'is_exposed', 'op': '=', 'value': False}, 'superevent') == Q(is_exposed=False)


def test_superevent_is_public_alias():
    assert q_only({'field': 'is_public', 'op': '=', 'value': True}, 'superevent') == Q(is_exposed=True)


def test_superevent_preferred_event():
    q, nd = t({'field': 'preferred_event', 'op': '=', 'value': 'G123456'}, 'superevent')
    assert q == Q(preferred_event__graceid__iexact='G123456')
    assert nd is False


def test_superevent_events_needs_distinct():
    q, nd = t({'field': 'events', 'op': '=', 'value': 'G123456'}, 'superevent')
    assert q == Q(events__graceid__iexact='G123456')
    assert nd is True


def test_superevent_event_alias():
    q, nd = t({'field': 'event', 'op': 'startswith', 'value': 'G12'}, 'superevent')
    assert q == Q(events__graceid__istartswith='G12')
    assert nd is True


# ---------------------------------------------------------------------------
# preferred_event.FOO delegation (superevent object_type)
# ---------------------------------------------------------------------------

def test_preferred_event_far_lt():
    q, nd = t({'field': 'preferred_event.far', 'op': '<', 'value': 1e-7}, 'superevent')
    assert q == Q(preferred_event__far__lt=1e-7)
    assert nd is False


def test_preferred_event_far_between():
    q, nd = t({'field': 'preferred_event.far', 'op': 'between', 'value': [1e-9, 1e-5]}, 'superevent')
    assert q == Q(preferred_event__far__range=[1e-9, 1e-5])
    assert nd is False


def test_preferred_event_far_is_null():
    q, nd = t({'field': 'preferred_event.far', 'op': 'is_null', 'value': True}, 'superevent')
    assert q == Q(preferred_event__far__isnull=True)
    assert nd is False


def test_preferred_event_group_eq():
    q, nd = t({'field': 'preferred_event.group', 'op': '=', 'value': 'CBC'}, 'superevent')
    assert q == Q(preferred_event__group__name__iexact='CBC')
    assert nd is False


def test_preferred_event_pipeline_contains():
    q, nd = t({'field': 'preferred_event.pipeline', 'op': 'contains', 'value': 'gstlal'}, 'superevent')
    assert q == Q(preferred_event__pipeline__name__icontains='gstlal')
    assert nd is False


def test_preferred_event_search_is_null():
    # db_enum with isnull_orm_path — both paths get prefixed
    q, nd = t({'field': 'preferred_event.search', 'op': 'is_null', 'value': True}, 'superevent')
    assert q == Q(preferred_event__search__isnull=True)
    assert nd is False


def test_preferred_event_gpstime_between():
    q, nd = t({'field': 'preferred_event.gpstime', 'op': 'between', 'value': [1187008882.0, 1187008900.0]}, 'superevent')
    assert q == Q(preferred_event__gpstime__range=[1187008882.0, 1187008900.0])
    assert nd is False


def test_preferred_event_si_snr_gt():
    # Attr sub-field via short alias: needs_distinct propagates from event schema
    q, nd = t({'field': 'preferred_event.si.snr', 'op': '>', 'value': 12.0}, 'superevent')
    assert q == Q(preferred_event__singleinspiral__snr__gt=12.0)
    assert nd is True


def test_preferred_event_si_snr_canonical():
    # Canonical form resolves identically to the short alias
    q, nd = t({'field': 'preferred_event.singleinspiral.snr', 'op': '>', 'value': 12.0}, 'superevent')
    assert q == Q(preferred_event__singleinspiral__snr__gt=12.0)
    assert nd is True


def test_preferred_event_submitter_contains():
    # Submitter: hardcoded Q paths receive the preferred_event__ prefix
    q, nd = t({'field': 'preferred_event.submitter', 'op': 'contains', 'value': 'einstein'}, 'superevent')
    expected = (Q(preferred_event__submitter__username__icontains='einstein') |
                Q(preferred_event__submitter__last_name__icontains='einstein'))
    assert q == expected
    assert nd is False


def test_preferred_event_label_has():
    # Label: uses _preferred_event_label_exists_q (event through-table, OuterRef preferred_event_id)
    q, nd = label_t({'field': 'preferred_event.label', 'op': 'has', 'value': 'EM_READY'}, 'superevent')
    assert _is_exists_q(q)
    assert nd is False


def test_preferred_event_label_not_has():
    q, nd = label_t({'field': 'preferred_event.label', 'op': 'not_has', 'value': 'DQV'}, 'superevent')
    assert _is_not_exists_q(q)
    assert nd is False


def test_preferred_event_graceid_unchanged():
    # The top-level 'preferred_event' field (graceid) is not affected by delegation
    q, nd = t({'field': 'preferred_event', 'op': '=', 'value': 'G123456'}, 'superevent')
    assert q == Q(preferred_event__graceid__iexact='G123456')
    assert nd is False


def test_preferred_event_far_shorthand_removed():
    # 'far' is no longer a valid superevent field — must use preferred_event.far
    from search.query.v2.schema import normalize_field_name
    assert normalize_field_name('far', 'superevent') is None


def test_validator_suggests_preferred_event_prefix():
    # When a user writes a bare event field name in a superevent query,
    # the error message should suggest the preferred_event.FOO form.
    from search.query.v2.validator import validate, QueryValidationError
    with pytest.raises(QueryValidationError) as exc_info:
        validate({'field': 'far', 'op': '<', 'value': 1e-7}, 'superevent')
    assert "preferred_event.far" in str(exc_info.value)


def test_validator_no_hint_for_truly_unknown_fields():
    # Completely unknown field should not get a misleading hint
    from search.query.v2.validator import validate, QueryValidationError
    with pytest.raises(QueryValidationError) as exc_info:
        validate({'field': 'banana', 'op': '=', 'value': 'x'}, 'superevent')
    assert "preferred_event" not in str(exc_info.value)


def test_validator_no_hint_for_excluded_event_fields():
    # Excluded back-reference fields should not be suggested
    from search.query.v2.validator import validate, QueryValidationError
    with pytest.raises(QueryValidationError) as exc_info:
        validate({'field': 'in_superevent', 'op': '=', 'value': True}, 'superevent')
    assert "preferred_event" not in str(exc_info.value)


def test_preferred_event_excluded_fields():
    # Circular back-references are excluded from delegation
    from search.query.v2.schema import normalize_field_name
    for field in ('preferred_event.superevent', 'preferred_event.in_superevent',
                  'preferred_event.is_preferred_event', 'preferred_event.runid'):
        assert normalize_field_name(field, 'superevent') is None, (
            f"Expected {field!r} to be excluded from preferred_event delegation"
        )


# ---------------------------------------------------------------------------
# Leaf: datetime fields
# ---------------------------------------------------------------------------

def test_created_lt():
    import pytz
    import datetime as dt
    q, _ = t({'field': 'created', 'op': '<', 'value': '2023-01-01T00:00:00Z'})
    expected_dt = pytz.utc.localize(dt.datetime(2023, 1, 1, 0, 0, 0))
    assert q == Q(created__lt=expected_dt)


def test_created_between():
    import pytz
    import datetime as dt
    q, _ = t({'field': 'created', 'op': 'between', 'value': ['2022-01-01', '2023-01-01']})
    lo = pytz.utc.localize(dt.datetime(2022, 1, 1))
    hi = pytz.utc.localize(dt.datetime(2023, 1, 1))
    assert q == Q(created__range=[lo, hi])


# ---------------------------------------------------------------------------
# Leaf: label conditions (structural tests using production models)
#
# We check that the returned Q contains Exists instances rather than comparing
# full Q equality, since Exists wraps a lazily-evaluated queryset object.
# ---------------------------------------------------------------------------

def _is_exists_q(q):
    """Return True if q is a single-child Q whose child is an Exists expression."""
    return (isinstance(q, Q) and not q.negated
            and len(q.children) == 1 and isinstance(q.children[0], Exists))


def _is_not_exists_q(q):
    """Return True if q is a negated single-child Q whose child is an Exists expression."""
    return (isinstance(q, Q) and q.negated
            and len(q.children) == 1 and isinstance(q.children[0], Exists))


def _collect_exists(q):
    """Recursively collect all Exists instances present anywhere in a Q tree."""
    found = []
    for child in q.children:
        if isinstance(child, Exists):
            found.append(child)
        elif isinstance(child, Q):
            found.extend(_collect_exists(child))
    return found


def test_label_has_produces_exists():
    q, nd = label_t({'field': 'label', 'op': 'has', 'value': 'EM_READY'})
    assert _is_exists_q(q)
    assert nd is False


def test_label_not_has_produces_not_exists():
    q, nd = label_t({'field': 'label', 'op': 'not_has', 'value': 'DQV'})
    assert _is_not_exists_q(q)
    assert nd is False


def test_label_and_two_labels():
    # AND of two label conditions: each child should be an Exists
    node = {'and': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'AND'
    exists_children = [c for c in q.children if isinstance(c, Exists)]
    assert len(exists_children) == 2


def test_label_and_with_non_label():
    node = {'and': [
        {'field': 'far', 'op': '<', 'value': 1e-5},
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'AND'
    # 'has' produces a bare Exists child (Q(Exists(...)) flattens under AND);
    # 'not_has' produces a negated Q child (negated Qs don't flatten).
    exists_direct = [c for c in q.children if isinstance(c, Exists)]
    assert len(exists_direct) == 1
    exists_negated = [c for c in q.children
                      if isinstance(c, Q) and c.negated
                      and any(isinstance(cc, Exists) for cc in c.children)]
    assert len(exists_negated) == 1


def test_label_or_two_labels():
    # OR of two label conditions — both become Exists; needs_distinct stays False
    node = {'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}
    q, nd = label_t(node)
    assert nd is False  # Exists does not multiply rows
    assert q.connector == 'OR'
    exists_children = [c for c in q.children if isinstance(c, Exists)]
    assert len(exists_children) == 2


def test_label_not_has_in_or():
    # not_has inside OR is now supported (Exists composes freely)
    node = {'or': [
        {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'


def test_label_and_inside_or():
    # AND(has_A, has_B) inside OR: previously broken, now correct with Exists
    node = {'or': [
        {'and': [
            {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
            {'field': 'label', 'op': 'has', 'value': 'DQV'},
        ]},
        {'field': 'far', 'op': '<', 'value': 1e-6},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'
    # First child should be an AND of two Exists
    and_child = q.children[0]
    assert isinstance(and_child, Q)
    assert and_child.connector == 'AND'
    exists_in_and = [c for c in and_child.children if isinstance(c, Exists)]
    assert len(exists_in_and) == 2


def test_label_not_has_superevent():
    q, nd = label_t({'field': 'label', 'op': 'not_has', 'value': 'DQV'}, 'superevent')
    assert _is_not_exists_q(q)
    assert nd is False


def test_not_label_has():
    # NOT(label has X) == not_has X: produces ~Exists
    node = {'not': {'field': 'label', 'op': 'has', 'value': 'DQV'}}
    q, nd = label_t(node)
    assert _is_not_exists_q(q)
    assert nd is False


def test_label_or_mixed_with_non_label():
    node = {'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'


def test_label_requires_model_class():
    # translate() without model_class raises when a label condition is present
    from search.query.v2.translator import _label_exists_q
    with pytest.raises(ValueError, match='model_class is required'):
        _label_exists_q('EM_READY', None)


# ---------------------------------------------------------------------------
# NOT combinator
# ---------------------------------------------------------------------------

def test_not_non_label():
    node = {'not': {'field': 'far', 'op': 'is_null', 'value': True}}
    assert q_only(node) == ~Q(far__isnull=True)


def test_not_neq_equivalent():
    node = {'not': {'field': 'far', 'op': '=', 'value': 1e-5}}
    assert q_only(node) == ~Q(far=1e-5)


# ---------------------------------------------------------------------------
# AND combinator
# ---------------------------------------------------------------------------

def test_and_two_conditions():
    node = {'and': [
        {'field': 'far', 'op': '<', 'value': 1e-5},
        {'field': 'gpstime', 'op': '>=', 'value': 1187008882.0},
    ]}
    q, nd = t(node)
    assert q == Q(far__lt=1e-5) & Q(gpstime__gte=1187008882.0)


def test_and_nested():
    node = {'and': [
        {'and': [
            {'field': 'group', 'op': '=', 'value': 'CBC'},
            {'field': 'pipeline', 'op': '=', 'value': 'gstlal'},
        ]},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, _ = t(node)
    expected = Q(group__name__iexact='CBC') & Q(pipeline__name__iexact='gstlal') & Q(far__lt=1e-5)
    assert q == expected


# ---------------------------------------------------------------------------
# OR combinator
# ---------------------------------------------------------------------------

def test_or_two_conditions():
    node = {'or': [
        {'field': 'far', 'op': '<', 'value': 1e-7},
        {'field': 'gpstime', 'op': '>', 'value': 1234567890.0},
    ]}
    q, _ = t(node)
    assert q == Q(far__lt=1e-7) | Q(gpstime__gt=1234567890.0)


def test_or_single_item():
    node = {'or': [{'field': 'far', 'op': '<', 'value': 1e-5}]}
    assert q_only(node) == Q(far__lt=1e-5)


# ---------------------------------------------------------------------------
# Nested combinators
# ---------------------------------------------------------------------------

def test_and_or_nested():
    node = {'and': [
        {'or': [
            {'field': 'group', 'op': '=', 'value': 'CBC'},
            {'field': 'group', 'op': '=', 'value': 'Burst'},
        ]},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, _ = t(node)
    expected = (Q(group__name__iexact='CBC') | Q(group__name__iexact='Burst')) & Q(far__lt=1e-5)
    assert q == expected


def test_not_and():
    node = {'not': {'and': [
        {'field': 'far', 'op': '<', 'value': 1e-5},
        {'field': 'gpstime', 'op': '>', 'value': 1e9},
    ]}}
    q, _ = t(node)
    assert q == ~(Q(far__lt=1e-5) & Q(gpstime__gt=1e9))


def test_bare_leaf():
    q, nd = t({'field': 'far', 'op': '<', 'value': 1e-5})
    assert q == Q(far__lt=1e-5)


# ---------------------------------------------------------------------------
# Attribute sub-table fields
# ---------------------------------------------------------------------------

def test_si_snr_gt():
    q, nd = t({'field': 'si.snr', 'op': '>', 'value': 12.0})
    assert q == Q(singleinspiral__snr__gt=12.0)
    assert nd is True  # SI requires distinct


def test_si_mass1_between():
    q, nd = t({'field': 'si.mass1', 'op': 'between', 'value': [1.0, 3.0]})
    assert q == Q(singleinspiral__mass1__range=[1.0, 3.0])
    assert nd is True


def test_singleinspiral_long_form():
    q, nd = t({'field': 'singleinspiral.snr', 'op': '>', 'value': 10.0})
    assert q == Q(singleinspiral__snr__gt=10.0)
    assert nd is True


def test_ci_mchirp_between():
    q, nd = t({'field': 'ci.mchirp', 'op': 'between', 'value': [1.0, 5.0]})
    assert q == Q(coincinspiralevent__mchirp__range=[1.0, 5.0])
    assert nd is False


def test_ci_long_form():
    q, nd = t({'field': 'coincinspiralevent.snr', 'op': '>=', 'value': 8.0})
    assert q == Q(coincinspiralevent__snr__gte=8.0)


def test_ci_coincinspiral_alias():
    q, _ = t({'field': 'coincinspiral.mass', 'op': '<', 'value': 3.0})
    assert q == Q(coincinspiralevent__mass__lt=3.0)


def test_mb_snr():
    q, nd = t({'field': 'mb.snr', 'op': '>', 'value': 5.0})
    assert q == Q(multiburstevent__snr__gt=5.0)
    assert nd is False


def test_ml_mchirp():
    q, _ = t({'field': 'ml.mchirp', 'op': 'between', 'value': [1.0, 10.0]})
    assert q == Q(mlyburstevent__mchirp__range=[1.0, 10.0])


def test_grb_trigger_id():
    q, _ = t({'field': 'grb.trigger_id', 'op': '=', 'value': 'GBM240825'})
    assert q == Q(grbevent__trigger_id='GBM240825')


def test_grb_trigger_id_contains():
    q, _ = t({'field': 'grb.trigger_id', 'op': 'contains', 'value': 'GBM'})
    assert q == Q(grbevent__trigger_id__icontains='GBM')


def test_si_ifo():
    q, nd = t({'field': 'si.ifo', 'op': '=', 'value': 'H1'})
    assert q == Q(singleinspiral__ifo='H1')
    assert nd is True


# ---------------------------------------------------------------------------
# Default filter injection
# ---------------------------------------------------------------------------

def test_inject_default_filter_event_no_category():
    tree = {'field': 'far', 'op': '<', 'value': 1e-5}
    wrapped = inject_default_filter(tree, 'event')
    assert 'and' in wrapped
    children = wrapped['and']
    assert len(children) == 2
    assert children[1] == tree


def test_inject_default_filter_event_with_group():
    tree = {'and': [
        {'field': 'group', 'op': '=', 'value': 'CBC'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    wrapped = inject_default_filter(tree, 'event')
    assert wrapped is tree


def test_inject_default_filter_superevent_no_category():
    tree = {'field': 't_0', 'op': '>', 'value': 1234567890.0}
    wrapped = inject_default_filter(tree, 'superevent')
    assert 'and' in wrapped


def test_inject_default_filter_superevent_with_id():
    tree = {'field': 'id', 'op': '=', 'value': 'S230904a'}
    wrapped = inject_default_filter(tree, 'superevent')
    assert wrapped is tree


def test_default_filter_superevent_q():
    default = build_default_filter('superevent')
    q, _ = translate(default, 'superevent')
    assert q == ~Q(category='T') & ~Q(category='M')


def test_default_filter_event_q():
    default = build_default_filter('event')
    q, _ = translate(default, 'event')
    assert q == ~Q(group__name__iexact='Test') & ~Q(search__name__iexact='MDC')


# ---------------------------------------------------------------------------
# Validator: field and operator checks
# ---------------------------------------------------------------------------

def test_validate_unknown_field_raises():
    with pytest.raises(QueryValidationError) as exc:
        validate({'field': 'nonexistent_xyz', 'op': '=', 'value': 'foo'}, 'event')
    assert 'nonexistent_xyz' in str(exc.value)


def test_validate_wrong_op_for_field():
    with pytest.raises(QueryValidationError):
        validate({'field': 'submitter', 'op': '=', 'value': 'foo'}, 'event')


def test_validate_bad_category():
    with pytest.raises(QueryValidationError):
        validate({'field': 'category', 'op': '=', 'value': 'BadCategory'}, 'superevent')


def test_validate_category_case_insensitive():
    result = validate({'field': 'category', 'op': '=', 'value': 'production'}, 'superevent', strict=False)
    assert result == []


def test_validate_bad_runid():
    with pytest.raises(QueryValidationError):
        validate({'field': 'runid', 'op': '=', 'value': 'O99'}, 'event')


def test_validate_label_op():
    with pytest.raises(QueryValidationError):
        validate({'field': 'far', 'op': 'has', 'value': 'EM_READY'}, 'event')


def test_validate_not_has_in_or_is_valid():
    # not_has inside OR is now valid (translated via ~Exists)
    result = validate({'or': [
        {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}, 'event', strict=False)
    assert result == []


def test_validate_has_in_or_is_valid():
    result = validate({'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}, 'event', strict=False)
    assert result == []


def test_validate_not_label_in_or_is_valid():
    # NOT(has X) inside OR is now valid (translated via ~Exists)
    result = validate({'or': [
        {'not': {'field': 'label', 'op': 'has', 'value': 'DQV'}},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}, 'event', strict=False)
    assert result == []


def test_validate_between_wrong_type():
    with pytest.raises(QueryValidationError):
        validate({'field': 'far', 'op': 'between', 'value': [1e-5, 'oops']}, 'event')


def test_validate_is_null_non_bool():
    with pytest.raises(QueryValidationError):
        validate({'field': 'far', 'op': 'is_null', 'value': 'yes'}, 'event')


def test_validate_permissive_collects_all():
    errors = validate({'field': 'zzz', 'op': '=', 'value': 'x'}, 'event', strict=False)
    assert len(errors) >= 1
    assert any('zzz' in e['message'] for e in errors)


def test_validate_field_on_wrong_object_type():
    with pytest.raises(QueryValidationError):
        validate({'field': 't_0', 'op': '=', 'value': 1234567890.0}, 'event')


def test_validate_event_field_on_superevent():
    result = validate({'field': 'gpstime', 'op': '<', 'value': 1234567890.0},
                      'superevent', strict=False)
    assert result == []


def test_validate_si_field_on_superevent_invalid():
    with pytest.raises(QueryValidationError):
        validate({'field': 'si.snr', 'op': '>', 'value': 10.0}, 'superevent')


def test_validate_datetime_bad_format():
    with pytest.raises(QueryValidationError):
        validate({'field': 'created', 'op': '<', 'value': 'not-a-date'}, 'event')


def test_validate_and_empty_list():
    with pytest.raises(QueryValidationError):
        validate({'and': []}, 'event')


def test_validate_not_double_negative_label():
    # NOT(not_has X) is still rejected — confusing double-negative
    with pytest.raises(QueryValidationError):
        validate({'not': {'field': 'label', 'op': 'not_has', 'value': 'X'}}, 'event')


# ---------------------------------------------------------------------------
# Superevent ID translation
# ---------------------------------------------------------------------------
# get_filter_kwargs_for_date_id_lookup is pure computation (regex + date
# arithmetic) — no database access is required for any of these tests.

def test_superevent_id_startswith():
    q, _ = t({'field': 'id', 'op': 'startswith', 'value': 'S230904'}, 'superevent')
    assert q == Q(superevent_id__istartswith='S230904')


def test_superevent_id_eq_with_suffix():
    q, _ = t({'field': 'id', 'op': '=', 'value': 'S230904a'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == Q(**expected_kwargs)


def test_superevent_id_eq_auto_suffix_s():
    q, _ = t({'field': 'id', 'op': '=', 'value': 'S230904'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == Q(**expected_kwargs)


def test_superevent_id_eq_auto_suffix_gw():
    q, _ = t({'field': 'id', 'op': '=', 'value': 'GW150914'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('GW150914A')
    assert q == Q(**expected_kwargs)


def test_superevent_id_neq():
    q, _ = t({'field': 'id', 'op': '!=', 'value': 'S230904a'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == ~Q(**expected_kwargs)


def test_superevent_id_in():
    # 'in' reduces over _build_superevent_id_q for each value
    q, _ = t({'field': 'id', 'op': 'in', 'value': ['S230904a', 'S230905b']}, 'superevent')
    q1 = Q(**Superevent.get_filter_kwargs_for_date_id_lookup('S230904a'))
    q2 = Q(**Superevent.get_filter_kwargs_for_date_id_lookup('S230905b'))
    assert q == q1 | q2


def test_event_superevent_field():
    q, _ = t({'field': 'superevent', 'op': '=', 'value': 'S230904a'}, 'event')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    prefixed = {f'superevent__{k}': v for k, v in expected_kwargs.items()}
    assert q == Q(**prefixed)


# ---------------------------------------------------------------------------
# Deep nesting with labels — cases that were broken or impossible before
# the Exists refactor.
#
# Background: the old label_filter_chain approach split translation into a
# Q object (for non-label conditions) and a separate chain of .filter()
# calls (for labels).  This made it impossible to mix label and non-label
# conditions inside OR branches, and produced *incorrect* SQL for
# AND(label_A, label_B): both names had to match in a single JOIN row,
# which is impossible for a M2M relationship — so multi-label AND inside
# OR would silently return no results for those branches.
#
# With Exists each label condition becomes an independent EXISTS subquery
# that composes correctly with &, |, and ~ at any depth.
# ---------------------------------------------------------------------------

def test_or_of_multi_label_ands():
    """OR( AND(has_A, has_B), AND(has_C, not_has_D) )

    The central M2M AND correctness bug.  Old approach: each AND branch
    produced Q(labels__name='A') & Q(labels__name='B'), which requires one
    JOIN row to carry both label names simultaneously — impossible for a M2M
    table, so both AND branches always returned zero results.

    New approach: each label produces an independent EXISTS subquery.  Two
    Exists subqueries ANDed together correctly finds rows that have *both*
    labels.
    """
    node = {'or': [
        {'and': [
            {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
            {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
        ]},
        {'and': [
            {'field': 'label', 'op': 'has', 'value': 'GW_CANDIDATE'},
            {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
        ]},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'
    # Four label conditions → four independent Exists subqueries total
    assert len(_collect_exists(q)) == 4
    # Each OR branch is an AND whose direct/nested children include 2 Exists
    for branch in q.children:
        assert isinstance(branch, Q)
        assert branch.connector == 'AND'
        assert len(_collect_exists(branch)) == 2


def test_not_label_inside_or_branch():
    """OR( NOT(has_A), far < X )

    Previously the validator rejected NOT(label has X) inside an OR branch
    with "use 'not_has' directly" messaging.  The real reason was that the
    label_filter_chain split made OR-level label conditions unworkable.

    With Exists, NOT(has X) == ~Exists(...), which ORs cleanly.
    """
    node = {'or': [
        {'not': {'field': 'label', 'op': 'has', 'value': 'DQV'}},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'
    assert len(_collect_exists(q)) == 1
    # The NOT(has) branch must be a negated Q containing an Exists
    not_branches = [c for c in q.children if isinstance(c, Q) and c.negated]
    assert len(not_branches) == 1
    assert any(isinstance(cc, Exists) for cc in not_branches[0].children)


def test_not_over_multi_label_and():
    """NOT( AND(has_A, has_B) )

    De Morgan: NOT(A AND B).  With the old split there was no way to express
    this — the chain approach only supported .filter(labels__name=X) calls
    that could not be wrapped in a NOT.

    Result should be a single negated Q whose AND children are two Exists.
    """
    node = {'not': {'and': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}}
    q, nd = label_t(node)
    assert nd is False
    assert q.negated
    # The two Exists subqueries live inside the negated Q
    assert len(_collect_exists(q)) == 2


def test_and_of_or_labels_with_not_label():
    """AND( OR(has_A, has_B), NOT(has_C) )

    Combining an OR of labels with a NOT-label at the AND level.
    Old approach: NOT(label has X) inside a branch was blocked; even if
    allowed, mixing Q and chain returns was not supported at OR depth.
    """
    node = {'and': [
        {'or': [
            {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
            {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
        ]},
        {'not': {'field': 'label', 'op': 'has', 'value': 'DQV'}},
    ]}
    q, nd = label_t(node)
    assert nd is False
    # Three label conditions = three Exists subqueries
    assert len(_collect_exists(q)) == 3


def test_three_level_deep_label_nesting():
    """AND( OR( AND(has_A, has_B), far < X ), NOT(has_C) )

    Three levels of nesting with labels at levels 1 and 3.  Old approach
    could not handle labels at all inside OR sub-expressions; with Exists
    each level translates independently and the Q objects compose normally.
    """
    node = {'and': [
        {'or': [
            {'and': [
                {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
                {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
            ]},
            {'field': 'far', 'op': '<', 'value': 1e-6},
        ]},
        {'not': {'field': 'label', 'op': 'has', 'value': 'DQV'}},
    ]}
    q, nd = label_t(node)
    assert nd is False
    # Three label conditions across three levels of nesting
    assert len(_collect_exists(q)) == 3
    # The inner AND branch (deepest level) must contain exactly 2 Exists
    # It is reachable as: outer AND → OR branch → AND branch
    outer_and = q
    or_branch = next(c for c in outer_and.children
                     if isinstance(c, Q) and c.connector == 'OR')
    inner_and = next(c for c in or_branch.children
                     if isinstance(c, Q) and c.connector == 'AND')
    assert len(_collect_exists(inner_and)) == 2


def test_or_of_not_has_and_non_label_with_distinct():
    """OR( not_has_A, event startswith X ) on a superevent query.

    Previously blocked: not_has inside OR was rejected by the validator.
    Also verifies that needs_distinct is hoisted from the non-label branch
    (the events reverse-FK join multiplies rows) while the label branch
    contributes an Exists subquery that does not.
    """
    node = {'or': [
        {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
        {'field': 'event', 'op': 'startswith', 'value': 'G12'},
    ]}
    q, nd = label_t(node, 'superevent')
    # The events reverse-FK branch sets needs_distinct; NOT EXISTS does not —
    # but the OR node hoists the True from the events branch.
    assert nd is True
    assert q.connector == 'OR'
    assert len(_collect_exists(q)) == 1


def test_mixed_label_and_non_label_three_conditions_in_or():
    """OR( has_A, not_has_B, far < X ) — three-branch OR mixing label types.

    All three cases (has, not_has, non-label) in a single OR.  This was
    completely impossible before because any label condition inside OR was
    blocked.
    """
    node = {'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'not_has', 'value': 'DQV'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    q, nd = label_t(node)
    assert nd is False
    assert q.connector == 'OR'
    # Two label conditions → two Exists subqueries
    assert len(_collect_exists(q)) == 2


# ---------------------------------------------------------------------------
# Missing operator coverage: graceid != and db_enum !=
# ---------------------------------------------------------------------------

def test_event_id_neq():
    assert q_only({'field': 'id', 'op': '!=', 'value': 'G123456'}) == ~Q(graceid__iexact='G123456')


def test_group_neq():
    assert q_only({'field': 'group', 'op': '!=', 'value': 'Test'}) == ~Q(group__name__iexact='Test')


def test_pipeline_neq():
    assert q_only({'field': 'pipeline', 'op': '!=', 'value': 'CWB'}) == ~Q(pipeline__name__iexact='CWB')


def test_superevent_preferred_event_neq():
    # graceid != on a superevent's preferred_event field
    q, nd = t({'field': 'preferred_event', 'op': '!=', 'value': 'G123456'}, 'superevent')
    assert q == ~Q(preferred_event__graceid__iexact='G123456')
    assert nd is False


# ---------------------------------------------------------------------------
# Additional datetime operator coverage
# ---------------------------------------------------------------------------

def test_created_eq():
    import pytz
    import datetime as dt
    q, _ = t({'field': 'created', 'op': '=', 'value': '2023-01-01'})
    expected_dt = pytz.utc.localize(dt.datetime(2023, 1, 1))
    assert q == Q(created=expected_dt)


def test_created_neq():
    import pytz
    import datetime as dt
    q, _ = t({'field': 'created', 'op': '!=', 'value': '2023-01-01'})
    expected_dt = pytz.utc.localize(dt.datetime(2023, 1, 1))
    assert q == ~Q(created=expected_dt)


def test_created_gt():
    import pytz
    import datetime as dt
    q, _ = t({'field': 'created', 'op': '>', 'value': '2023-06-15T12:00:00Z'})
    expected_dt = pytz.utc.localize(dt.datetime(2023, 6, 15, 12, 0, 0))
    assert q == Q(created__gt=expected_dt)


# ---------------------------------------------------------------------------
# Validator: missing cases
# ---------------------------------------------------------------------------

def test_validate_between_lo_gt_hi_numeric():
    with pytest.raises(QueryValidationError, match='lo'):
        validate({'field': 'far', 'op': 'between', 'value': [1e-3, 1e-10]}, 'event')


def test_validate_between_lo_gt_hi_datetime():
    with pytest.raises(QueryValidationError, match='lo'):
        validate({'field': 'created', 'op': 'between',
                  'value': ['2024-01-01', '2023-01-01']}, 'event')


def test_validate_in_empty_list():
    with pytest.raises(QueryValidationError, match='non-empty'):
        validate({'field': 'group', 'op': 'in', 'value': []}, 'event')


def test_validate_or_empty_list():
    # 'or' with empty children list is invalid (mirrors the existing and test)
    with pytest.raises(QueryValidationError):
        validate({'or': []}, 'event')


# ---------------------------------------------------------------------------
# inject_default_filter: gaps
# ---------------------------------------------------------------------------

def test_inject_default_filter_event_with_graceid_alias():
    # 'graceid' is an alias for 'id' — should suppress the default filter
    tree = {'field': 'graceid', 'op': '=', 'value': 'G123456'}
    assert inject_default_filter(tree, 'event') is tree


def test_inject_default_filter_event_with_search():
    # 'search' in the query should suppress the default filter
    tree = {'field': 'search', 'op': '=', 'value': 'AllSky'}
    assert inject_default_filter(tree, 'event') is tree


def test_inject_default_filter_suppress_field_in_nested_or():
    # Suppress field found inside an OR branch
    tree = {'or': [
        {'field': 'group', 'op': '=', 'value': 'CBC'},
        {'field': 'far', 'op': '<', 'value': 1e-5},
    ]}
    assert inject_default_filter(tree, 'event') is tree


def test_inject_default_filter_suppress_field_in_nested_not():
    # Suppress field found inside a NOT wrapper
    tree = {'not': {'field': 'group', 'op': '=', 'value': 'Test'}}
    assert inject_default_filter(tree, 'event') is tree


def test_inject_default_filter_superevent_with_category_in_and():
    # Category inside AND suppresses the default filter
    tree = {'and': [
        {'field': 'category', 'op': '=', 'value': 'Production'},
        {'field': 't_0', 'op': '>', 'value': 1234567890.0},
    ]}
    assert inject_default_filter(tree, 'superevent') is tree


# ---------------------------------------------------------------------------
# Database integration tests
#
# These tests create real Event and Superevent objects and verify that the
# Q objects produced by translate() filter the queryset correctly.
# The core value: structural Q-equality tests cannot catch wrong ORM paths
# or incorrect label semantics (e.g., the M2M AND bug).
# ---------------------------------------------------------------------------

@pytest.fixture
def db_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='translator.db.test')
    return user


@pytest.fixture
def make_event(db_user):
    """Factory: make_event(...) → Event saved to the test DB."""
    from events.models import Group, Pipeline, Search, Label, Labelling

    def factory(group_name='CBC', pipeline_name='GstLAL', search_name=None,
                gpstime=1000.0, far=None, labels=()):
        group, _ = Group.objects.get_or_create(name=group_name)
        pipeline, _ = Pipeline.objects.get_or_create(name=pipeline_name)
        kwargs = {
            'group': group,
            'pipeline': pipeline,
            'submitter': db_user,
            'gpstime': gpstime,
        }
        if search_name is not None:
            search, _ = Search.objects.get_or_create(name=search_name)
            kwargs['search'] = search
        if far is not None:
            kwargs['far'] = far
        event = Event.objects.create(**kwargs)
        # Event.save() has a quirk: on first save it calls compute() which
        # only returns the graceid value without persisting it.  A second
        # save() goes through the else branch → ComputedFieldsModel.save()
        # properly computes and stores graceid in the DB.
        event.save()
        for name in labels:
            label, _ = Label.objects.get_or_create(name=name)
            Labelling.objects.create(event=event, label=label, creator=db_user)
        return event

    return factory


@pytest.fixture
def make_superevent(db_user, make_event):
    """Factory: make_superevent(...) → Superevent saved to the test DB."""
    from events.models import Label
    from superevents.models import Labelling as SupereventLabelling

    def factory(t_0=1000.0,
                category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
                is_gw=False, labels=()):
        event = make_event()
        se = Superevent.objects.create(
            t_start=t_0 - 1,
            t_0=t_0,
            t_end=t_0 + 1,
            preferred_event=event,
            submitter=db_user,
            category=category,
            is_gw=is_gw,
        )
        for name in labels:
            label, _ = Label.objects.get_or_create(name=name)
            SupereventLabelling.objects.create(
                superevent=se, label=label, creator=db_user)
        return se

    return factory


@pytest.mark.django_db
def test_db_event_filter_by_group(make_event):
    cbc = make_event(group_name='CBC')
    burst = make_event(group_name='Burst')
    q, _ = t({'field': 'group', 'op': '=', 'value': 'CBC'})
    results = list(Event.objects.filter(q))
    assert cbc in results
    assert burst not in results


@pytest.mark.django_db
def test_db_event_filter_by_far(make_event):
    low_far = make_event(far=1e-12)
    high_far = make_event(far=1e-3)
    no_far = make_event()
    q, _ = t({'field': 'far', 'op': '<', 'value': 1e-10})
    results = list(Event.objects.filter(q))
    assert low_far in results
    assert high_far not in results
    assert no_far not in results


@pytest.mark.django_db
def test_db_event_filter_and(make_event):
    match = make_event(group_name='CBC', far=1e-12)
    wrong_far = make_event(group_name='CBC', far=1e-3)
    wrong_group = make_event(group_name='Burst', far=1e-12)
    node = {'and': [
        {'field': 'group', 'op': '=', 'value': 'CBC'},
        {'field': 'far', 'op': '<', 'value': 1e-10},
    ]}
    q, _ = t(node)
    results = list(Event.objects.filter(q))
    assert match in results
    assert wrong_far not in results
    assert wrong_group not in results


@pytest.mark.django_db
def test_db_event_filter_or(make_event):
    cbc = make_event(group_name='CBC')
    burst = make_event(group_name='Burst')
    external = make_event(group_name='External')
    node = {'or': [
        {'field': 'group', 'op': '=', 'value': 'CBC'},
        {'field': 'group', 'op': '=', 'value': 'Burst'},
    ]}
    q, _ = t(node)
    results = list(Event.objects.filter(q))
    assert cbc in results
    assert burst in results
    assert external not in results


@pytest.mark.django_db
def test_db_event_filter_not(make_event):
    cbc = make_event(group_name='CBC')
    test_event = make_event(group_name='Test')
    q, _ = t({'not': {'field': 'group', 'op': '=', 'value': 'Test'}})
    results = list(Event.objects.filter(q))
    assert cbc in results
    assert test_event not in results


@pytest.mark.django_db
def test_db_event_filter_label_has(make_event):
    labelled = make_event(labels=['EM_READY'])
    unlabelled = make_event()
    q, _ = label_t({'field': 'label', 'op': 'has', 'value': 'EM_READY'})
    results = list(Event.objects.filter(q))
    assert labelled in results
    assert unlabelled not in results


@pytest.mark.django_db
def test_db_event_filter_label_and_both_required(make_event):
    """AND(has EM_READY, has ADVOK) must require BOTH labels.

    This is the core M2M correctness bug: the old Q(labels__name='A') &
    Q(labels__name='B') approach generated a single JOIN condition requiring
    one row in the through-table to carry both label names simultaneously,
    which is impossible.  With Exists subqueries each label is checked
    independently, so AND correctly requires both to be present.
    """
    both = make_event(labels=['EM_READY', 'ADVOK'])
    only_em_ready = make_event(labels=['EM_READY'])
    neither = make_event()
    node = {'and': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}
    q, _ = label_t(node)
    results = list(Event.objects.filter(q))
    assert both in results
    assert only_em_ready not in results
    assert neither not in results


@pytest.mark.django_db
def test_db_event_filter_label_or(make_event):
    em_ready = make_event(labels=['EM_READY'])
    advok = make_event(labels=['ADVOK'])
    neither = make_event()
    node = {'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}
    q, _ = label_t(node)
    results = list(Event.objects.filter(q))
    assert em_ready in results
    assert advok in results
    assert neither not in results


@pytest.mark.django_db
def test_db_event_filter_label_not_has(make_event):
    dqv = make_event(labels=['DQV'])
    clean = make_event()
    q, _ = label_t({'field': 'label', 'op': 'not_has', 'value': 'DQV'})
    results = list(Event.objects.filter(q))
    assert clean in results
    assert dqv not in results


@pytest.mark.django_db
def test_db_event_filter_label_or_mixed_with_non_label(make_event):
    """OR(has EM_READY, far < 1e-10) with both branches satisfied by different events."""
    by_label = make_event(labels=['EM_READY'], far=1.0)
    by_far = make_event(far=1e-12)
    neither = make_event(far=1.0)
    node = {'or': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'far', 'op': '<', 'value': 1e-10},
    ]}
    q, _ = label_t(node)
    results = list(Event.objects.filter(q))
    assert by_label in results
    assert by_far in results
    assert neither not in results


@pytest.mark.django_db
def test_db_superevent_filter_by_category(make_superevent):
    prod = make_superevent(category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)
    test = make_superevent(category=Superevent.SUPEREVENT_CATEGORY_TEST,
                           t_0=2000.0)
    q, _ = t({'field': 'category', 'op': '=', 'value': 'Production'}, 'superevent')
    results = list(Superevent.objects.filter(q))
    assert prod in results
    assert test not in results


@pytest.mark.django_db
def test_db_superevent_filter_label_and_both_required(make_superevent):
    """AND(has EM_READY, has ADVOK) on superevents requires both labels."""
    both = make_superevent(labels=['EM_READY', 'ADVOK'])
    one = make_superevent(labels=['EM_READY'], t_0=2000.0)
    node = {'and': [
        {'field': 'label', 'op': 'has', 'value': 'EM_READY'},
        {'field': 'label', 'op': 'has', 'value': 'ADVOK'},
    ]}
    q, _ = label_t(node, 'superevent')
    results = list(Superevent.objects.filter(q))
    assert both in results
    assert one not in results


@pytest.mark.django_db
def test_db_superevent_filter_label_not_has(make_superevent):
    dqv = make_superevent(labels=['DQV'])
    clean = make_superevent(t_0=2000.0)
    q, _ = label_t({'field': 'label', 'op': 'not_has', 'value': 'DQV'}, 'superevent')
    results = list(Superevent.objects.filter(q))
    assert clean in results
    assert dqv not in results


# ---------------------------------------------------------------------------
# needs_distinct integration tests
#
# Some ORM paths multiply result rows via JOINs.  The translator signals this
# with needs_distinct=True; callers must call .distinct() on the queryset.
# These tests verify the behaviour with real DB rows:
#
#   - singleinspiral.*: one-to-many FK from Event means one event with N
#     matching SI rows produces N duplicate rows without DISTINCT.
#   - superevent.events.*: reverse FK means one superevent with N matching
#     associated events produces N duplicate rows without DISTINCT.
# ---------------------------------------------------------------------------

@pytest.fixture
def make_single_inspiral(make_event):
    """Factory: create a SingleInspiral row attached to the given event."""
    from events.models import SingleInspiral

    def factory(event, snr=10.0, ifo='H1'):
        return SingleInspiral.objects.create(event=event, snr=snr, ifo=ifo)

    return factory


# needs_distinct is a static schema property; translate() is pure computation.
def test_db_si_snr_needs_distinct_flag():
    """translate() reports needs_distinct=True for singleinspiral fields."""
    q, nd = t({'field': 'si.snr', 'op': '>', 'value': 8.0})
    assert nd is True


@pytest.mark.django_db
def test_db_si_snr_without_distinct_duplicates(make_event, make_single_inspiral):
    """Without DISTINCT, one event with two matching SI rows appears twice."""
    event = make_event()
    make_single_inspiral(event, snr=15.0, ifo='H1')
    make_single_inspiral(event, snr=12.0, ifo='L1')
    q, _ = t({'field': 'si.snr', 'op': '>', 'value': 8.0})
    # No .distinct() — expect duplicate rows
    results = list(Event.objects.filter(q))
    assert results.count(event) == 2


@pytest.mark.django_db
def test_db_si_snr_with_distinct_no_duplicates(make_event, make_single_inspiral):
    """With DISTINCT, an event with two matching SI rows appears exactly once,
    while an event whose only SI row is below the threshold is excluded."""
    event = make_event()
    make_single_inspiral(event, snr=15.0, ifo='H1')
    make_single_inspiral(event, snr=12.0, ifo='L1')
    # Confirm the duplicate exists before asserting distinct() removes it
    q, nd = t({'field': 'si.snr', 'op': '>', 'value': 8.0})
    assert nd is True
    assert Event.objects.filter(q).count() == 2  # two rows, same event

    other = make_event()
    make_single_inspiral(other, snr=5.0, ifo='H1')  # below threshold — should not appear
    results = list(Event.objects.filter(q).distinct())
    assert results.count(event) == 1
    assert other not in results


@pytest.mark.django_db
def test_db_si_snr_single_row_unaffected_by_distinct(make_event, make_single_inspiral):
    """An event with exactly one matching SI row appears once with or without
    DISTINCT — distinct() must not suppress legitimate results."""
    event = make_event()
    make_single_inspiral(event, snr=20.0, ifo='H1')
    q, _ = t({'field': 'si.snr', 'op': '>', 'value': 8.0})
    assert list(Event.objects.filter(q).distinct()) == [event]


# needs_distinct is a static schema property; translate() is pure computation.
def test_db_superevent_events_needs_distinct_flag():
    """translate() reports needs_distinct=True for superevent.events field."""
    q, nd = t({'field': 'events', 'op': 'startswith', 'value': 'G'}, 'superevent')
    assert nd is True


@pytest.mark.django_db
def test_db_superevent_events_without_distinct_duplicates(make_event, make_superevent):
    """Without DISTINCT, a superevent with two matching associated events
    appears twice in the results."""
    se = make_superevent()
    # se.events.add() issues a raw FK UPDATE, bypassing Event.save(), so the
    # graceid already stored by make_event is preserved unchanged.
    extra = make_event(gpstime=2000.0)
    se.events.add(extra)

    q, _ = t({'field': 'events', 'op': 'startswith', 'value': 'G'}, 'superevent')
    results = list(Superevent.objects.filter(q))
    assert results.count(se) == 2


@pytest.mark.django_db
def test_db_superevent_events_with_distinct_no_duplicates(make_event, make_superevent):
    """With DISTINCT, each superevent appears exactly once even when multiple
    associated events match; the pre-distinct duplicate count confirms the
    fix is needed."""
    se = make_superevent()
    extra = make_event(gpstime=2000.0)
    se.events.add(extra)

    other_se = make_superevent(t_0=5000.0)

    q, nd = t({'field': 'events', 'op': 'startswith', 'value': 'G'}, 'superevent')
    assert nd is True
    # Without distinct: se appears twice (two matching events), other_se once
    assert Superevent.objects.filter(q).count() == 3
    results = list(Superevent.objects.filter(q).distinct())
    assert results.count(se) == 1
    assert results.count(other_se) == 1


@pytest.mark.django_db
def test_db_superevent_events_non_matching_graceid_excluded(make_event, make_superevent):
    """A superevent whose associated events all have non-'G' graceid prefixes
    must not appear when filtering for graceid startswith 'G'."""
    # Test-group events get graceid 'T<N>', not 'G<N>'
    test_event = make_event(group_name='Test')
    se_test = Superevent.objects.create(
        t_start=999.0, t_0=1000.0, t_end=1001.0,
        preferred_event=test_event,
        submitter=test_event.submitter,
        category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
    )
    # A normal superevent with a CBC event (graceid starts with 'G') for contrast
    se_cbc = make_superevent(t_0=5000.0)

    q, _ = t({'field': 'events', 'op': 'startswith', 'value': 'G'}, 'superevent')
    results = list(Superevent.objects.filter(q))
    assert se_cbc in results
    assert se_test not in results
