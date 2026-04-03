"""
GraceDB v2 search query ORM translator.

Walks a validated query tree and produces a pair:

    (Q_object, needs_distinct)

``Q_object``
    A ``django.db.models.Q`` instance encoding all conditions, including
    label conditions expressed as ``Exists`` subqueries.

``needs_distinct``
    True if the queryset must have ``.distinct()`` applied.  Set when:
      - Any ``singleinspiral.*`` field is used (FK with multiple rows per event).
      - The ``events`` superevent field is used (reverse FK).

Label semantics
    Label ``has`` and ``not_has`` conditions are translated using correlated
    ``Exists`` subqueries against the M2M through table (EventLabel or
    SupereventLabel).  This is required to correctly express:

      - AND of multiple labels: ``has A AND has B``
        → ``Exists(A) & Exists(B)`` (two independent subqueries)
      - NOT of a label: ``NOT(has A)`` / ``not_has A``
        → ``~Exists(A)`` (NOT EXISTS — correct NOT-EXISTS semantics)
      - OR including labels: ``(has A) OR (far < 1e-6)``
        → ``Exists(A) | Q(far__lt=1e-6)`` (composes freely)

    Using ``labels__name='foo'`` JOINs instead would cause row multiplication
    (requiring DISTINCT) and makes AND semantics impossible to express as a
    single Q composition.

    ``model_class`` must be provided to ``translate()`` whenever the query
    contains any label condition, so that the through table can be resolved
    via model introspection.

Usage::

    from search.query.v2.translator import translate, apply_query
    from events.models import Event

    q, distinct = translate(tree, 'event', Event)
    qs = Event.objects.filter(q)
    if distinct:
        qs = qs.distinct()

    # Or all at once:
    qs = apply_query(Event, tree, 'event')
"""

import datetime
import re
from functools import reduce

import pytz
from django.db.models import Exists, OuterRef, Q

from .schema import (
    OP_SUFFIX,
    SUPEREVENT_CATEGORY_MAP,
    normalize_field_name,
    get_field_schema,
)
from ...constants import RUN_MAP_FLAT
from ...utils import run_map_search_filter


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Superevent ID patterns that lack a letter suffix and need one appended.
# GW-prefix IDs use uppercase suffix ('A'); all others use lowercase ('a').
_GW_ID_RE = re.compile(r'^((?:T|M)?)GW(\d+)$', re.IGNORECASE)
_S_ID_RE  = re.compile(r'^((?:T|M)?)S(\d+)$',  re.IGNORECASE)

_UTC = pytz.utc


def _parse_datetime(value):
    """
    Parse an ISO 8601 datetime string to a timezone-aware datetime object.
    Assumes UTC if no timezone is given.
    """
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return _UTC.localize(datetime.datetime.strptime(value, fmt))
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def _superevent_id_auto_suffix(raw_id):
    """
    If *raw_id* has no letter suffix, append the first letter.
    GW-prefix → 'A'; all others → 'a'.
    Matches the auto-suffix logic in v1 superevents.py.
    """
    m = _GW_ID_RE.match(raw_id)
    if m:
        return m.group(1).upper() + 'GW' + m.group(2) + 'A'
    m = _S_ID_RE.match(raw_id)
    if m:
        return m.group(1).upper() + 'S' + m.group(2) + 'a'
    return raw_id  # already has a suffix (or unknown format — let get_filter_kwargs raise)


def _build_superevent_id_q(raw_id, prefix=''):
    """
    Build a Q object for an exact superevent ID match using
    ``Superevent.get_filter_kwargs_for_date_id_lookup``.

    ``prefix`` is prepended to every key (e.g., 'superevent__' for event →
    superevent FK lookups).
    """
    from superevents.models import Superevent
    id_with_suffix = _superevent_id_auto_suffix(raw_id)
    kwargs = Superevent.get_filter_kwargs_for_date_id_lookup(id_with_suffix)
    if prefix:
        p = prefix if prefix.endswith('__') else prefix + '__'
        kwargs = {f'{p}{k}': v for k, v in kwargs.items()}
    return Q(**kwargs)


def _label_exists_q(label_name, model_class):
    """
    Build a Q(Exists(...)) subquery for "model instance has label *label_name*".

    Uses model introspection to find the M2M through table and the FK field
    pointing back to *model_class*, so this works for both Event and Superevent
    without hardcoding model names.

    Use ``~_label_exists_q(...)`` for ``not_has`` (NOT EXISTS).
    """
    if model_class is None:
        raise ValueError(
            "model_class is required when the query contains label conditions. "
            "Pass the model class (e.g., Event or Superevent) to translate()."
        )
    through = model_class._meta.get_field('labels').remote_field.through
    fk_name = next(
        f.name for f in through._meta.get_fields()
        if hasattr(f, 'related_model') and f.related_model == model_class
    )
    return Q(Exists(through.objects.filter(
        **{fk_name: OuterRef('pk'), 'label__name': label_name}
    )))


def _preferred_event_label_exists_q(label_name, model_class):
    """
    Build a Q(Exists(...)) subquery for "the superevent's preferred event has
    label *label_name*".

    *model_class* is the **Superevent** model class.  We navigate via the
    ``preferred_event`` FK to reach the Event model, then use Event's label
    M2M through table filtered by ``event_id = OuterRef('preferred_event_id')``.

    Use ``~_preferred_event_label_exists_q(...)`` for ``not_has``.
    """
    if model_class is None:
        raise ValueError(
            "model_class is required when the query contains label conditions. "
            "Pass the model class (e.g., Superevent) to translate()."
        )
    event_model = model_class._meta.get_field('preferred_event').related_model
    through = event_model._meta.get_field('labels').remote_field.through
    fk_name = next(
        f.name for f in through._meta.get_fields()
        if hasattr(f, 'related_model') and f.related_model == event_model
    )
    return Q(Exists(through.objects.filter(
        **{fk_name: OuterRef('preferred_event_id'), 'label__name': label_name}
    )))


# ---------------------------------------------------------------------------
# Leaf translation
# ---------------------------------------------------------------------------

def _translate_leaf(node, object_type, model_class):
    """
    Translate a single leaf node.

    Returns (Q_object, needs_distinct).
    """
    raw_field = node['field']
    op        = node['op']
    value     = node['value']

    canonical = normalize_field_name(raw_field, object_type)
    schema    = get_field_schema(canonical, object_type)

    field_type = schema['type']
    orm_path   = schema.get('orm_path')

    # True when translating a preferred_event.FOO field on a superevent query.
    # The schema's orm_path is already prefixed ('preferred_event__...') by
    # _make_preferred_event_schema, so most field types need no special handling.
    # Only 'label' and 'submitter' construct Q paths outside of orm_path and
    # need explicit awareness of the prefix.
    pref_event = (
        object_type == 'superevent'
        and canonical is not None
        and canonical.startswith('preferred_event.')
    )

    # ----------------------------------------------------------------
    # Label fields: always use Exists subqueries
    # ----------------------------------------------------------------
    if field_type == 'label':
        if pref_event:
            q = _preferred_event_label_exists_q(value, model_class)
        else:
            q = _label_exists_q(value, model_class)
        if op == 'not_has':
            q = ~q
        return q, False

    # ----------------------------------------------------------------
    # Virtual enum: runid
    # ----------------------------------------------------------------
    if field_type == 'virtual_enum':
        gps_field = orm_path  # e.g., 'gpstime' or 't_0'
        run_q = run_map_search_filter(value, gps_field)
        return run_q, False

    # ----------------------------------------------------------------
    # Submitter: OR of username__icontains and last_name__icontains
    # ----------------------------------------------------------------
    if field_type == 'submitter':
        prefix = 'preferred_event__' if pref_event else ''
        q = (Q(**{f'{prefix}submitter__username__icontains': value}) |
             Q(**{f'{prefix}submitter__last_name__icontains': value}))
        return q, False

    # ----------------------------------------------------------------
    # Boolean derived: in_superevent, is_preferred_event
    # Stored as isnull path; user-supplied value is inverted.
    # ----------------------------------------------------------------
    if field_type == 'boolean_derived':
        invert = schema.get('invert_value', False)
        isnull_value = (not value) if invert else value
        return Q(**{orm_path: isnull_value}), False

    # ----------------------------------------------------------------
    # Superevent ID (the 'id' field on superevents)
    # ----------------------------------------------------------------
    if field_type == 'superevent_id':
        nd = schema.get('needs_distinct', False)
        if op == '=':
            return _build_superevent_id_q(value), nd
        elif op == '!=':
            return ~_build_superevent_id_q(value), nd
        elif op == 'startswith':
            return Q(superevent_id__istartswith=value), nd
        elif op == 'in':
            q = reduce(Q.__or__,
                       [_build_superevent_id_q(v) for v in value],
                       Q())
            return q, nd
        raise ValueError(
            f"Operator '{op}' is not handled for field type 'superevent_id'. "
            f"This is a bug — the validator should have rejected it."
        )

    # ----------------------------------------------------------------
    # Superevent ID reference (the 'superevent' FK field on events)
    # ----------------------------------------------------------------
    if field_type == 'superevent_id_ref':
        fk_prefix = orm_path  # 'superevent'
        q = _build_superevent_id_q(value, prefix=fk_prefix)
        return q, False

    # ----------------------------------------------------------------
    # Superevent category: translate human-readable name to DB code
    # ----------------------------------------------------------------
    if field_type == 'superevent_category':
        db_value = SUPEREVENT_CATEGORY_MAP.get(value.lower(), value) if isinstance(value, str) else value
        if op == '=':
            return Q(**{orm_path: db_value}), False
        elif op == '!=':
            return ~Q(**{orm_path: db_value}), False
        elif op == 'in':
            db_values = [SUPEREVENT_CATEGORY_MAP.get(v.lower(), v) for v in value]
            return Q(**{f'{orm_path}__in': db_values}), False
        raise ValueError(
            f"Operator '{op}' is not handled for field type 'superevent_category'. "
            f"This is a bug — the validator should have rejected it."
        )

    # ----------------------------------------------------------------
    # Datetime fields: parse ISO 8601 before building Q
    # ----------------------------------------------------------------
    if field_type == 'datetime':
        if op == 'between':
            lo, hi = _parse_datetime(value[0]), _parse_datetime(value[1])
            return Q(**{f'{orm_path}__range': [lo, hi]}), False
        elif op == '!=':
            return ~Q(**{orm_path: _parse_datetime(value)}), False
        elif op in ('=', '<', '<=', '>', '>='):
            return Q(**{f'{orm_path}{OP_SUFFIX[op]}': _parse_datetime(value)}), False
        raise ValueError(
            f"Operator '{op}' is not handled for field type 'datetime'. "
            f"This is a bug — the validator should have rejected it."
        )

    # ----------------------------------------------------------------
    # DB enum fields (group, pipeline, search, ci.ifos, etc.)
    # Use case-insensitive comparisons since values come from user input.
    # ----------------------------------------------------------------
    if field_type == 'db_enum':
        if op == 'is_null':
            # Use the special isnull path if defined (for FK-nullable fields)
            isnull_path = schema.get('isnull_orm_path', f'{orm_path}__isnull')
            return Q(**{isnull_path: value}), False
        elif op == '=':
            return Q(**{f'{orm_path}__iexact': value}), False
        elif op == '!=':
            return ~Q(**{f'{orm_path}__iexact': value}), False
        elif op == 'contains':
            return Q(**{f'{orm_path}__icontains': value}), False
        elif op == 'in':
            # Build OR of iexact comparisons for case-insensitive IN
            q = reduce(Q.__or__,
                       [Q(**{f'{orm_path}__iexact': v}) for v in value],
                       Q())
            return q, False
        raise ValueError(
            f"Operator '{op}' is not handled for field type 'db_enum'. "
            f"This is a bug — the validator should have rejected it."
        )

    # ----------------------------------------------------------------
    # Graceid fields (event id, preferred_event, events)
    # Use case-insensitive match since graceid encodes category in prefix.
    # ----------------------------------------------------------------
    if field_type == 'graceid':
        nd = schema.get('needs_distinct', False)
        if op == '=':
            return Q(**{f'{orm_path}__iexact': value}), nd
        elif op == '!=':
            return ~Q(**{f'{orm_path}__iexact': value}), nd
        elif op == 'startswith':
            return Q(**{f'{orm_path}__istartswith': value}), nd
        elif op == 'in':
            q = reduce(Q.__or__,
                       [Q(**{f'{orm_path}__iexact': v}) for v in value],
                       Q())
            return q, nd
        raise ValueError(
            f"Operator '{op}' is not handled for field type 'graceid'. "
            f"This is a bug — the validator should have rejected it."
        )

    # ----------------------------------------------------------------
    # General numeric / string / boolean fields
    # ----------------------------------------------------------------
    nd = schema.get('needs_distinct', False)

    if op == 'is_null':
        return Q(**{f'{orm_path}__isnull': value}), nd

    if op == '!=':
        return ~Q(**{orm_path: value}), nd

    if op == 'between':
        return Q(**{f'{orm_path}__range': value}), nd

    if op not in OP_SUFFIX:
        raise ValueError(
            f"Operator '{op}' has no ORM suffix mapping. "
            f"This is a bug — the validator should have rejected it."
        )
    return Q(**{f'{orm_path}{OP_SUFFIX[op]}': value}), nd


# ---------------------------------------------------------------------------
# Combinator translation
# ---------------------------------------------------------------------------

def _translate_node(node, object_type, model_class):
    """
    Recursively translate a query tree node.

    Returns (Q_object, needs_distinct).
    """
    # ---- AND ----
    if 'and' in node:
        children = node['and']
        if not children:
            return Q(), False
        combined_q = Q()
        combined_distinct = False
        for child in children:
            q, nd = _translate_node(child, object_type, model_class)
            combined_q &= q
            combined_distinct = combined_distinct or nd
        return combined_q, combined_distinct

    # ---- OR ----
    if 'or' in node:
        children = node['or']
        if not children:
            return Q(), False
        child_qs = []
        combined_distinct = False
        for child in children:
            q, nd = _translate_node(child, object_type, model_class)
            child_qs.append(q)
            combined_distinct = combined_distinct or nd
        return reduce(Q.__or__, child_qs, Q()), combined_distinct

    # ---- NOT ----
    if 'not' in node:
        q, nd = _translate_node(node['not'], object_type, model_class)
        return ~q, nd

    # ---- Leaf ----
    return _translate_leaf(node, object_type, model_class)


# ---------------------------------------------------------------------------
# Default filter injection
# ---------------------------------------------------------------------------

def _tree_has_field(node, field_names):
    """
    Return True if the tree contains any leaf whose raw field name is in
    *field_names*.  Callers must include all alias forms in *field_names*
    since field names are not normalised here.
    """
    if not isinstance(node, dict):
        return False
    if 'and' in node:
        return any(_tree_has_field(c, field_names) for c in node['and'])
    if 'or' in node:
        return any(_tree_has_field(c, field_names) for c in node['or'])
    if 'not' in node:
        return _tree_has_field(node['not'], field_names)
    return node.get('field', '') in field_names


def build_default_filter(object_type):
    """
    Return the default exclusion filter tree for *object_type*.

    Events:      exclude Test group and MDC search
    Superevents: exclude Test and MDC categories
    """
    if object_type == 'superevent':
        return {
            'and': [
                {'field': 'category', 'op': '!=', 'value': 'Test'},
                {'field': 'category', 'op': '!=', 'value': 'MDC'},
            ]
        }
    else:  # event
        return {
            'and': [
                {'field': 'group',  'op': '!=', 'value': 'Test'},
                {'field': 'search', 'op': '!=', 'value': 'MDC'},
            ]
        }


# Fields whose presence in the tree suppresses the default exclusion filter.
_NO_DEFAULT_FIELDS = {
    'event':      frozenset(['id', 'graceid', 'group', 'search']),
    'superevent': frozenset(['id', 'superevent_id', 'category']),
}


def inject_default_filter(user_tree, object_type):
    """
    Wrap *user_tree* with the default exclusion filter if the tree does
    not already contain a condition on category/group/search/id.

    Returns a (possibly wrapped) tree dict.
    """
    suppress_fields = _NO_DEFAULT_FIELDS.get(object_type, frozenset())
    if _tree_has_field(user_tree, suppress_fields):
        return user_tree
    default = build_default_filter(object_type)
    return {'and': [default, user_tree]}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate(node, object_type, model_class=None):
    """
    Translate a validated v2 query tree to Django ORM components.

    Args:
        node:        Validated query tree dict.
        object_type: ``'event'`` or ``'superevent'``.
        model_class: Django model class (e.g., ``Event`` or ``Superevent``).
                     Required if the query contains any ``label`` conditions;
                     used to resolve the M2M through table for Exists subqueries.

    Returns:
        A 2-tuple ``(Q_object, needs_distinct)``:
          - ``Q_object``: ``django.db.models.Q`` for all conditions.
          - ``needs_distinct``: bool — True if ``.distinct()`` must be applied.
    """
    return _translate_node(node, object_type, model_class)


def apply_query(model_class, node, object_type):
    """
    Translate and execute a v2 query tree, returning a QuerySet.

    Does NOT inject the default category filter — call ``inject_default_filter``
    first if the default exclusion behaviour is desired.

    Args:
        model_class: Django model class (Event or Superevent).
        node:        Validated query tree dict.
        object_type: ``'event'`` or ``'superevent'``.

    Returns:
        A Django QuerySet.
    """
    q, needs_distinct = translate(node, object_type, model_class)
    qs = model_class.objects.filter(q)
    if needs_distinct:
        qs = qs.distinct()
    return qs
