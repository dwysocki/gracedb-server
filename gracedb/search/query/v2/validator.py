"""
GraceDB v2 search query semantic validator.

Checks an incoming query dict against the field schema *after* JSON Schema
structural validation has already passed.  This layer verifies:
  - Every ``field`` is a known field for the given ``object_type``
  - Every ``op`` is in the field's allowed operator list
  - ``value`` is of the correct Python type for the field and operator
  - ``between`` values satisfy lo <= hi
  - ``in`` arrays are non-empty and homogeneous
  - ``runid`` values are known run IDs
  - ``category`` values are one of Production/Test/MDC
  - ``NOT(label not_has X)`` is rejected as confusing double-negative syntax

Two modes are supported:
  - Strict (default): raises ``QueryValidationError`` on the first error.
  - Permissive: collects all errors and returns them as a list of dicts.

Usage::

    from search.query.v2.validator import validate, QueryValidationError

    try:
        validate(query_tree, 'superevent')
    except QueryValidationError as e:
        return 400, {'error': str(e), 'path': e.path}

    # Permissive mode:
    errors = validate(query_tree, 'event', strict=False)
"""

import datetime
import numbers

from .schema import (
    get_field_schema, normalize_field_name,
    SUPEREVENT_CATEGORY_CHOICES, VALID_RUN_IDS,
)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class QueryValidationError(Exception):
    """
    Raised when semantic validation of a v2 query tree fails.

    Attributes:
        message (str): human-readable description of the problem
        path (list):   tree-path to the failing node, e.g. ['and', 1, 'or', 0]
    """
    def __init__(self, message, path=None):
        super().__init__(message)
        self.message = message
        self.path = path or []

    def __str__(self):
        if self.path:
            return f'{self.message} (at {_format_path(self.path)})'
        return self.message


def _format_path(path):
    """Convert a path list to a readable string: ['and', 1, 'or', 0] → 'and[1].or[0]'"""
    parts = []
    for i, segment in enumerate(path):
        if isinstance(segment, int):
            parts.append(f'[{segment}]')
        elif parts:
            parts.append(f'.{segment}')
        else:
            parts.append(str(segment))
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Type-checking helpers
# ---------------------------------------------------------------------------

def _is_numeric(v):
    return isinstance(v, numbers.Number) and not isinstance(v, bool)


def _is_string(v):
    return isinstance(v, str)


def _is_bool(v):
    return isinstance(v, bool)


def _validate_value_for_field(schema, op, value, path):
    """
    Return an error dict (or None) for the given (schema, op, value) triple.
    Does NOT raise — the caller handles raising vs collecting.
    """
    field_type = schema['type']

    # --- is_null ---
    if op == 'is_null':
        if not _is_bool(value):
            return {'message': f"'is_null' requires a boolean value", 'path': path}
        return None

    # --- between ---
    if op == 'between':
        if not isinstance(value, list) or len(value) != 2:
            return {'message': "'between' requires a 2-element array [lo, hi]", 'path': path}
        lo, hi = value
        if field_type == 'datetime':
            err = _check_datetime_value(lo, path) or _check_datetime_value(hi, path)
            if err:
                return err
        elif field_type in ('float', 'gpstime', 'integer'):
            if not (_is_numeric(lo) and _is_numeric(hi)):
                return {'message': "'between' on a numeric field requires numeric values", 'path': path}
            if lo > hi:
                return {'message': f"'between' range: lo ({lo}) must be <= hi ({hi})", 'path': path}
        return None

    # --- in ---
    if op == 'in':
        if not isinstance(value, list) or len(value) == 0:
            return {'message': "'in' requires a non-empty array", 'path': path}
        for elem in value:
            err = _validate_scalar_value(field_type, elem, path)
            if err:
                return err
        return None

    # --- has / not_has ---
    if op in ('has', 'not_has'):
        if not _is_string(value):
            return {'message': f"'{op}' requires a string (label name)", 'path': path}
        return None

    # --- scalar operators ---
    return _validate_scalar_value(field_type, value, path)


def _validate_scalar_value(field_type, value, path):
    """Check that a scalar value matches the field type. Returns error dict or None."""
    if field_type in ('float', 'gpstime', 'integer'):
        if not _is_numeric(value):
            return {'message': f"Expected a number, got {type(value).__name__}", 'path': path}
    elif field_type in ('boolean', 'boolean_derived'):
        if not _is_bool(value):
            return {'message': "Expected true or false", 'path': path}
    elif field_type == 'datetime':
        return _check_datetime_value(value, path)
    elif field_type == 'superevent_category':
        if not _is_string(value):
            return {'message': "Expected a string (Production, Test, or MDC)", 'path': path}
        if value.lower() not in ('production', 'test', 'mdc'):
            return {
                'message': (f"Unknown category '{value}'. "
                            f"Valid values: {', '.join(SUPEREVENT_CATEGORY_CHOICES)}"),
                'path': path,
            }
    elif field_type == 'virtual_enum':
        if not _is_string(value):
            return {'message': "Expected a run ID string (e.g., O3, O4b)", 'path': path}
        if value.upper() not in VALID_RUN_IDS and value not in VALID_RUN_IDS:
            return {'message': f"Unknown run ID '{value}'", 'path': path}
    elif field_type in ('string', 'db_enum', 'instruments', 'graceid',
                        'superevent_id', 'superevent_id_ref', 'label', 'submitter'):
        if not _is_string(value):
            return {'message': f"Expected a string, got {type(value).__name__}", 'path': path}
    return None


def _check_datetime_value(value, path):
    """Validate that value is a parseable ISO 8601 datetime string."""
    if not _is_string(value):
        return {'message': f"Datetime field requires an ISO 8601 string, got {type(value).__name__}", 'path': path}
    # Accept common formats
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            datetime.datetime.strptime(value, fmt)
            return None
        except ValueError:
            continue
    return {'message': f"Cannot parse datetime '{value}'. Use ISO 8601 (e.g., 2017-08-17T12:41:04Z)", 'path': path}


# ---------------------------------------------------------------------------
# Core recursive validator
# ---------------------------------------------------------------------------

def _add_error(errors, strict, message, path):
    """Add an error to the list, or raise immediately if strict."""
    err = QueryValidationError(message, path)
    if strict:
        raise err
    errors.append({'message': message, 'path': list(path)})


def _validate_node(node, object_type, path, errors, strict):
    """Recursively validate a query tree node."""
    if not isinstance(node, dict):
        _add_error(errors, strict, f"Query node must be a JSON object, got {type(node).__name__}", path)
        return

    keys = set(node.keys())

    # ---- AND combinator ----
    if 'and' in keys:
        unexpected = keys - {'and'}
        if unexpected:
            _add_error(errors, strict,
                f"'and' node must not have extra keys: {unexpected}", path)
        children = node['and']
        if not isinstance(children, list) or len(children) == 0:
            _add_error(errors, strict, "'and' must be a non-empty list", path + ['and'])
            return
        for i, child in enumerate(children):
            _validate_node(child, object_type, path + ['and', i], errors, strict)
        return

    # ---- OR combinator ----
    if 'or' in keys:
        unexpected = keys - {'or'}
        if unexpected:
            _add_error(errors, strict,
                f"'or' node must not have extra keys: {unexpected}", path)
        children = node['or']
        if not isinstance(children, list) or len(children) == 0:
            _add_error(errors, strict, "'or' must be a non-empty list", path + ['or'])
            return
        for i, child in enumerate(children):
            _validate_node(child, object_type, path + ['or', i], errors, strict)
        return

    # ---- NOT combinator ----
    if 'not' in keys:
        unexpected = keys - {'not'}
        if unexpected:
            _add_error(errors, strict,
                f"'not' node must not have extra keys: {unexpected}", path)
        child = node['not']
        # Reject NOT(label not_has X) — equivalent to (label has X) but the
        # double-negative phrasing is needlessly confusing.
        if (isinstance(child, dict) and child.get('op') == 'not_has'
                and _field_is_label(child.get('field', ''), object_type)):
            _add_error(errors, strict,
                "NOT(label not_has ...) is redundant; use 'has' directly", path + ['not'])
        else:
            _validate_node(child, object_type, path + ['not'], errors, strict)
        return

    # ---- Leaf node ----
    if 'field' in keys:
        unexpected = keys - {'field', 'op', 'value'}
        if unexpected:
            _add_error(errors, strict,
                f"Leaf node has unexpected keys: {unexpected}", path)

        raw_field = node.get('field')
        op = node.get('op')
        value = node.get('value')

        if raw_field is None:
            _add_error(errors, strict, "Missing 'field'", path); return
        if op is None:
            _add_error(errors, strict, "Missing 'op'", path); return
        if value is None and op != 'is_null':
            _add_error(errors, strict, "Missing 'value'", path); return

        # Resolve field name
        canonical = normalize_field_name(raw_field, object_type)
        if canonical is None:
            _add_error(errors, strict,
                f"Unknown field '{raw_field}' for object type '{object_type}'", path)
            return

        schema = get_field_schema(canonical, object_type)

        # Check operator is allowed for this field
        if op not in schema['operators']:
            allowed = ', '.join(schema['operators'])
            _add_error(errors, strict,
                f"Operator '{op}' is not allowed for field '{canonical}'. "
                f"Allowed operators: {allowed}", path)
            return

        # Validate value type
        if value is not None:
            err = _validate_value_for_field(schema, op, value, path)
            if err:
                _add_error(errors, strict, err['message'], err['path'])
        return

    # ---- Unknown node shape ----
    _add_error(errors, strict,
        f"Node must have 'field' (leaf), 'and', 'or', or 'not' key. Got: {list(keys)}",
        path)


def _field_is_label(field, object_type):
    """Return True if the given field name resolves to a label-type field."""
    schema = get_field_schema(field, object_type)
    return schema is not None and schema['type'] == 'label'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate(node, object_type, strict=True):
    """
    Validate a v2 query tree against the field schema.

    Args:
        node:        The query tree dict (from JSON.loads / yaml.safe_load).
        object_type: ``'event'`` or ``'superevent'``.
        strict:      If True (default), raises ``QueryValidationError`` on the
                     first problem found. If False, collects all errors and
                     returns them as a list of dicts with 'message' and 'path'
                     keys (empty list = valid).

    Returns:
        ``None`` if strict and valid.
        A (possibly empty) list of error dicts if not strict.

    Raises:
        ``QueryValidationError`` if strict and the tree is invalid.
    """
    if object_type not in ('event', 'superevent'):
        raise QueryValidationError(
            f"Unknown object_type '{object_type}'. Must be 'event' or 'superevent'."
        )

    errors = []
    _validate_node(node, object_type, [], errors, strict)
    if not strict:
        return errors
    return None
