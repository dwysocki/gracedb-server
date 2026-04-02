"""
Tests for the v2 query translator.

Tests in this file are unit tests for the translate() function.  They compare
Q objects directly (Django Q supports equality comparison) and inspect the
needs_distinct return value.

Label conditions are tested structurally (checking for Exists instances) using
the test_gracedb models, which have the same M2M label shape as the production
models.  No database access is required — model metadata and lazy QuerySet
construction work without hitting the DB.

Tests that require database access (e.g., superevent ID lookups via
get_filter_kwargs_for_date_id_lookup) are marked with @pytest.mark.django_db.
"""
import importlib
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


# test_gracedb model stubs — same M2M label structure as production models,
# used to provide model_class for label Exists tests (no DB access needed).
from test_gracedb.models import Event as _TestEvent
from test_gracedb.models import Superevent as _TestSuperevent


def _try_import(module_name):
    """Import module_name and skip the test if it cannot be imported.

    pytest.importorskip only handles ImportError; Django also raises
    RuntimeError when a required app is missing from INSTALLED_APPS.
    """
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        pytest.skip(f"Cannot import {module_name!r}: {exc}")


def label_t(node, object_type='event'):
    """Translate a tree that contains label conditions."""
    mc = _TestEvent if object_type == 'event' else _TestSuperevent
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


def test_superevent_far_shorthand():
    assert q_only({'field': 'far', 'op': '<', 'value': 1e-7}, 'superevent') == Q(preferred_event__far__lt=1e-7)


def test_superevent_far_between():
    q, _ = t({'field': 'far', 'op': 'between', 'value': [1e-9, 1e-5]}, 'superevent')
    assert q == Q(preferred_event__far__range=[1e-9, 1e-5])


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
# Leaf: label conditions (structural tests using test_gracedb models)
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
# Superevent ID translation (requires django_db for get_filter_kwargs)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_superevent_id_startswith():
    q, _ = t({'field': 'id', 'op': 'startswith', 'value': 'S230904'}, 'superevent')
    assert q == Q(superevent_id__istartswith='S230904')


@pytest.mark.django_db
def test_superevent_id_eq_with_suffix():
    Superevent = _try_import('superevents.models').Superevent
    q, _ = t({'field': 'id', 'op': '=', 'value': 'S230904a'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == Q(**expected_kwargs)


@pytest.mark.django_db
def test_superevent_id_eq_auto_suffix_s():
    Superevent = _try_import('superevents.models').Superevent
    q, _ = t({'field': 'id', 'op': '=', 'value': 'S230904'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == Q(**expected_kwargs)


@pytest.mark.django_db
def test_superevent_id_eq_auto_suffix_gw():
    Superevent = _try_import('superevents.models').Superevent
    q, _ = t({'field': 'id', 'op': '=', 'value': 'GW150914'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('GW150914A')
    assert q == Q(**expected_kwargs)


@pytest.mark.django_db
def test_superevent_id_neq():
    Superevent = _try_import('superevents.models').Superevent
    q, _ = t({'field': 'id', 'op': '!=', 'value': 'S230904a'}, 'superevent')
    expected_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup('S230904a')
    assert q == ~Q(**expected_kwargs)


@pytest.mark.django_db
def test_event_superevent_field():
    Superevent = _try_import('superevents.models').Superevent
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
