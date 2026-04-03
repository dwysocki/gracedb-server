"""
GraceDB v2 search query schema.

This module is the single source of truth for:
  - Which fields are searchable on events and superevents
  - Which operators each field accepts
  - The Django ORM path(s) for each field
  - Type information used by the validator and translator

Attribute sub-table fields (si.snr, ci.mchirp, etc.) are enumerated
explicitly using only indexed database fields to avoid full-table scans.
"""

from ...constants import RUN_MAP_FLAT

# ---------------------------------------------------------------------------
# Operator constants
# ---------------------------------------------------------------------------

COMPARISON_OPS          = ['=', '!=', '<', '<=', '>', '>=', 'between']
NULLABLE_COMPARISON_OPS = COMPARISON_OPS + ['is_null']  # for fields that can be NULL in the DB
STRING_OPS_FULL = ['=', '!=', 'contains', 'startswith', 'in', 'is_null']
STRING_OPS_BASIC = ['=', '!=', 'contains', 'in']
ENUM_OPS = ['=', '!=', 'in']
BOOLEAN_OPS = ['=']
LABEL_OPS = ['has', 'not_has']
ID_OPS = ['=', '!=', 'startswith', 'in']

# ---------------------------------------------------------------------------
# ORM lookup suffix for each operator
# Note: '!=' and 'has'/'not_has' are handled specially in the translator.
# ---------------------------------------------------------------------------

OP_SUFFIX = {
    '=':          '',
    '<':          '__lt',
    '<=':         '__lte',
    '>':          '__gt',
    '>=':         '__gte',
    'between':    '__range',
    'in':         '__in',
    'contains':   '__icontains',
    'startswith': '__istartswith',
    'is_null':    '__isnull',
}

# ---------------------------------------------------------------------------
# Superevent category encoding
# Maps lowercase human-readable name → single-char DB code
#
# These must match superevents.models.Superevent.SUPEREVENT_CATEGORY_* and
# SUPEREVENT_CATEGORY_CHOICES. We cannot import from that model here because
# the superevents app is not installed in the local test environment; keep
# these in sync manually if the model ever changes.
# ---------------------------------------------------------------------------

SUPEREVENT_CATEGORY_MAP = {
    'production': 'P',
    'test':       'T',
    'mdc':        'M',
}
# Human-readable labels (accepted case-insensitively by the validator)
SUPEREVENT_CATEGORY_CHOICES = ['Production', 'Test', 'MDC']

# Valid run ID names (from RUN_MAP_FLAT, normalised to uppercase for lookup)
VALID_RUN_IDS = set(RUN_MAP_FLAT.keys())

# Event fields excluded from preferred_event.FOO delegation on superevents.
# These either reference the superevent relationship (circular) or expand
# using a GPS field name that has no meaning in the preferred_event context.
_EXCLUDED_PREFERRED_EVENT_FIELDS = frozenset({
    'superevent',          # superevent_id_ref — circular back-reference
    'in_superevent',       # boolean_derived from superevent FK — always True
    'is_preferred_event',  # boolean_derived from preferred_for FK — always True
    'runid',               # virtual_enum that expands a GPS field by name
})

# ---------------------------------------------------------------------------
# Attribute sub-table definitions
# Only indexed fields are listed (see events/models.py Meta.indexes).
# ---------------------------------------------------------------------------

# Short alias → canonical Django ORM model name (table prefix for ORM paths)
TABLE_ALIASES = {
    'si':            'singleinspiral',
    'ci':            'coincinspiralevent',
    'mb':            'multiburstevent',
    'ml':            'mlyburstevent',
    'grb':           'grbevent',
    'coincinspiral': 'coincinspiralevent',
    'multiburst':    'multiburstevent',
}

# Reverse map: canonical ORM name → preferred short alias
TABLE_SHORT_FORM = {
    'singleinspiral':     'si',
    'coincinspiralevent': 'ci',
    'multiburstevent':    'mb',
    'mlyburstevent':      'ml',
    'grbevent':           'grb',
}

# {canonical_table_name: {field_name: (type_str, allowed_ops)}}
_ATTR_FIELD_DEFS = {
    'singleinspiral': {
        'ifo':     ('string', ['=', '!=', 'contains', 'in', 'is_null']),
        'search':  ('string', ['=', '!=', 'contains', 'in', 'is_null']),
        'channel': ('string', ['=', '!=', 'contains', 'startswith', 'is_null']),
        'mass1':   ('float',  NULLABLE_COMPARISON_OPS),
        'mass2':   ('float',  NULLABLE_COMPARISON_OPS),
        'mchirp':  ('float',  NULLABLE_COMPARISON_OPS),
        'mtotal':  ('float',  NULLABLE_COMPARISON_OPS),
        'snr':     ('float',  NULLABLE_COMPARISON_OPS),
        'chisq':   ('float',  NULLABLE_COMPARISON_OPS),
    },
    'coincinspiralevent': {
        'ifos':             ('string', ['=', 'contains', 'is_null']),
        'mass':             ('float',  NULLABLE_COMPARISON_OPS),
        'mchirp':           ('float',  NULLABLE_COMPARISON_OPS),
        'minimum_duration': ('float',  NULLABLE_COMPARISON_OPS),
        'snr':              ('float',  NULLABLE_COMPARISON_OPS),
        'false_alarm_rate': ('float',  NULLABLE_COMPARISON_OPS),
        'combined_far':     ('float',  NULLABLE_COMPARISON_OPS),
    },
    'multiburstevent': {
        'ifos':             ('string',  ['=', 'contains', 'is_null']),
        'start_time':       ('integer', NULLABLE_COMPARISON_OPS),
        'duration':         ('float',   NULLABLE_COMPARISON_OPS),
        'peak_time':        ('integer', NULLABLE_COMPARISON_OPS),
        'central_freq':     ('float',   NULLABLE_COMPARISON_OPS),
        'mchirp':           ('float',   NULLABLE_COMPARISON_OPS),
        'snr':              ('float',   NULLABLE_COMPARISON_OPS),
        'code':             ('string',  ['=', '!=', 'contains', 'in', 'is_null']),
        'single_ifo_times': ('string',  ['=', 'contains', 'is_null']),
    },
    'mlyburstevent': {
        'ifos':                ('string', ['=', 'contains', 'is_null']),
        'score_coinc':         ('float',  NULLABLE_COMPARISON_OPS),
        'score_coher':         ('float',  NULLABLE_COMPARISON_OPS),
        'score_comb':          ('float',  NULLABLE_COMPARISON_OPS),
        'central_freq':        ('float',  NULLABLE_COMPARISON_OPS),
        'bandwidth':           ('float',  NULLABLE_COMPARISON_OPS),
        'duration':            ('float',  NULLABLE_COMPARISON_OPS),
        'snr':                 ('float',  NULLABLE_COMPARISON_OPS),
        'detection_statistic': ('float',  NULLABLE_COMPARISON_OPS),
        'central_time':        ('float',  NULLABLE_COMPARISON_OPS),
        'bbh':                 ('float',  NULLABLE_COMPARISON_OPS),
        'sglf':                ('float',  NULLABLE_COMPARISON_OPS),
        'sghf':                ('float',  NULLABLE_COMPARISON_OPS),
        'background':          ('float',  NULLABLE_COMPARISON_OPS),
        'glitch':              ('float',  NULLABLE_COMPARISON_OPS),
        'freq_correlation':    ('float',  NULLABLE_COMPARISON_OPS),
        'mass1':               ('float',  NULLABLE_COMPARISON_OPS),
        'mass2':               ('float',  NULLABLE_COMPARISON_OPS),
        'mchirp':              ('float',  NULLABLE_COMPARISON_OPS),
        'mtotal':              ('float',  NULLABLE_COMPARISON_OPS),
        'spin1z':              ('float',  NULLABLE_COMPARISON_OPS),
        'spin2z':              ('float',  NULLABLE_COMPARISON_OPS),
    },
    'grbevent': {
        'trigger_id': ('string', ['=', '!=', 'contains', 'startswith', 'in', 'is_null']),
    },
}


def _build_attr_fields():
    """
    Generate schema entries for all attribute sub-table fields.

    Each field is registered under its canonical key (e.g., 'singleinspiral.snr').
    Short-form input (e.g., 'si.snr') is accepted by normalize_field_name,
    which resolves it to the canonical key via TABLE_ALIASES before any lookup.

    help_text uses the short alias form since that is what users are shown.
    TABLE_SHORT_FORM[table_canonical] will raise KeyError if a table is added
    to _ATTR_FIELD_DEFS without a corresponding short alias entry.
    """
    result = {}
    for table_canonical, fields in _ATTR_FIELD_DEFS.items():
        short = TABLE_SHORT_FORM[table_canonical]
        needs_distinct = table_canonical == 'singleinspiral'
        for field_name, (type_, ops) in fields.items():
            result[f'{table_canonical}.{field_name}'] = {
                'type':           type_,
                'operators':      ops,
                'orm_path':       f'{table_canonical}__{field_name}',
                'needs_distinct': needs_distinct,
                'help_text':      f'{short}.{field_name}',
            }
    return result


def _make_preferred_event_schema(event_schema_entry):
    """
    Return a copy of an event field schema dict adapted for use as a
    ``preferred_event.FOO`` field on a superevent.

    The ORM path (and ``isnull_orm_path``, if present) is prefixed with
    ``'preferred_event__'`` so the translator can use it directly without
    any additional manipulation.  The ``type``, ``operators``,
    ``needs_distinct``, and any other keys are copied unchanged.
    """
    entry = dict(event_schema_entry)
    if entry.get('orm_path') is not None:
        entry['orm_path'] = 'preferred_event__' + entry['orm_path']
    if 'isnull_orm_path' in entry:
        entry['isnull_orm_path'] = 'preferred_event__' + entry['isnull_orm_path']
    entry['help_text'] = 'Preferred event: ' + entry.get('help_text', '')
    return entry


# ---------------------------------------------------------------------------
# Core field schema: events
# ---------------------------------------------------------------------------

_EVENT_CORE_FIELDS = {
    'id': {
        'type':           'graceid',
        'operators':      ID_OPS,
        'orm_path':       'graceid',
        'needs_distinct': False,
        'help_text':      'GraceDB event ID (e.g., G123456, T1234)',
    },
    'gpstime': {
        'type':           'gpstime',
        'operators':      NULLABLE_COMPARISON_OPS,
        'orm_path':       'gpstime',
        'needs_distinct': False,
        'help_text':      'GPS trigger time (seconds since GPS epoch)',
    },
    'far': {
        'type':           'float',
        'operators':      NULLABLE_COMPARISON_OPS,
        'orm_path':       'far',
        'needs_distinct': False,
        'help_text':      'False alarm rate (Hz)',
    },
    'instruments': {
        'type':           'string',
        'operators':      ['=', 'contains'],
        'orm_path':       'instruments',
        'needs_distinct': False,
        'help_text':      'Detector instruments (e.g., H1,L1,V1)',
    },
    'nevents': {
        'type':           'integer',
        'operators':      NULLABLE_COMPARISON_OPS,
        'orm_path':       'nevents',
        'needs_distinct': False,
        'help_text':      'Number of single-detector triggers in coincidence',
    },
    'created': {
        'type':           'datetime',
        'operators':      COMPARISON_OPS,
        'orm_path':       'created',
        'needs_distinct': False,
        'help_text':      'UTC datetime when the event was submitted (ISO 8601)',
    },
    'group': {
        # type 'db_enum': case-insensitive string match against FK name field
        'type':           'db_enum',
        'operators':      STRING_OPS_BASIC,
        'orm_path':       'group__name',
        'needs_distinct': False,
        'help_text':      'Analysis group (e.g., CBC, Burst, External)',
    },
    'pipeline': {
        'type':           'db_enum',
        'operators':      STRING_OPS_BASIC,
        'orm_path':       'pipeline__name',
        'needs_distinct': False,
        'help_text':      'Analysis pipeline (e.g., gstlal, pycbc, cWB)',
    },
    'search': {
        'type':            'db_enum',
        'operators':       STRING_OPS_FULL,
        'orm_path':        'search__name',
        # When op=='is_null', use this path instead (checks FK nullability,
        # not the name sub-field nullability)
        'isnull_orm_path': 'search__isnull',
        'needs_distinct':  False,
        'help_text':       'Search type (e.g., AllSky, LowMass, GRB)',
    },
    'submitter': {
        # Special type: OR of username__icontains and last_name__icontains
        'type':           'submitter',
        'operators':      ['contains'],
        'orm_path':       None,
        'needs_distinct': False,
        'help_text':      'Submitter username or last name (case-insensitive substring)',
    },
    'runid': {
        # Virtual field that expands to a GPS time range
        'type':           'virtual_enum',
        'operators':      ['='],
        'orm_path':       'gpstime',  # the GPS field to expand into
        'needs_distinct': False,
        'help_text':      'Observing run name (e.g., O3, O4b, ER16)',
    },
    'label': {
        'type':           'label',
        'operators':      LABEL_OPS,
        'orm_path':       'labels__name',
        'needs_distinct': False,
        'help_text':      'Applied label name (e.g., EM_READY, DQV)',
    },
    'in_superevent': {
        # Boolean derived from FK nullability; value is inverted for ORM
        'type':           'boolean_derived',
        'operators':      BOOLEAN_OPS,
        'orm_path':       'superevent__isnull',
        'invert_value':   True,  # in_superevent=True → isnull=False
        'needs_distinct': False,
        'help_text':      'True if event is associated with any superevent',
    },
    'is_preferred_event': {
        'type':           'boolean_derived',
        'operators':      BOOLEAN_OPS,
        'orm_path':       'superevent_preferred_for__isnull',
        'invert_value':   True,
        'needs_distinct': False,
        'help_text':      'True if event is the preferred event of a superevent',
    },
    'superevent': {
        # References a specific superevent by ID string
        'type':           'superevent_id_ref',
        'operators':      ['='],
        'orm_path':       'superevent',  # FK prefix used in get_filter_kwargs
        'needs_distinct': False,
        'help_text':      'Superevent ID this event belongs to',
    },
}

# ---------------------------------------------------------------------------
# Core field schema: superevents
# ---------------------------------------------------------------------------

_SUPEREVENT_CORE_FIELDS = {
    'id': {
        'type':           'superevent_id',
        'operators':      ID_OPS,
        # No simple orm_path: '=' uses get_filter_kwargs_for_date_id_lookup,
        # 'startswith' uses superevent_id__istartswith
        'orm_path':       None,
        'needs_distinct': False,
        'help_text':      'Superevent ID (e.g., S230904a, GW150914)',
    },
    't_0': {
        'type':           'gpstime',
        'operators':      COMPARISON_OPS,  # NOT NULL on superevents — is_null not meaningful
        'orm_path':       't_0',
        'needs_distinct': False,
        'help_text':      'Central trigger GPS time',
    },
    't_start': {
        'type':           'gpstime',
        'operators':      COMPARISON_OPS,  # NOT NULL on superevents
        'orm_path':       't_start',
        'needs_distinct': False,
        'help_text':      'Start of superevent time window (GPS)',
    },
    't_end': {
        'type':           'gpstime',
        'operators':      COMPARISON_OPS,  # NOT NULL on superevents
        'orm_path':       't_end',
        'needs_distinct': False,
        'help_text':      'End of superevent time window (GPS)',
    },
    'created': {
        'type':           'datetime',
        'operators':      COMPARISON_OPS,
        'orm_path':       'created',
        'needs_distinct': False,
        'help_text':      'UTC datetime when the superevent was created (ISO 8601)',
    },
    'category': {
        # Human-readable values (Production/Test/MDC) mapped to DB codes (P/T/M)
        'type':           'superevent_category',
        'operators':      ENUM_OPS,
        'orm_path':       'category',
        'needs_distinct': False,
        'help_text':      'Superevent category (Production, Test, MDC)',
    },
    'is_gw': {
        'type':           'boolean',
        'operators':      BOOLEAN_OPS,
        'orm_path':       'is_gw',
        'needs_distinct': False,
        'help_text':      'True if superevent has been confirmed as a gravitational wave',
    },
    'is_exposed': {
        'type':           'boolean',
        'operators':      BOOLEAN_OPS,
        'orm_path':       'is_exposed',
        'needs_distinct': False,
        'help_text':      'True if superevent is publicly visible',
    },
    'submitter': {
        'type':           'submitter',
        'operators':      ['contains'],
        'orm_path':       None,
        'needs_distinct': False,
        'help_text':      'Submitter username or last name (case-insensitive substring)',
    },
    'runid': {
        'type':           'virtual_enum',
        'operators':      ['='],
        'orm_path':       't_0',  # GPS field to expand into
        'needs_distinct': False,
        'help_text':      'Observing run name (e.g., O3, O4b, ER16)',
    },
    'label': {
        'type':           'label',
        'operators':      LABEL_OPS,
        'orm_path':       'labels__name',
        'needs_distinct': False,
        'help_text':      'Applied label name (e.g., EM_READY, DQV)',
    },
    'preferred_event': {
        'type':           'graceid',
        'operators':      ID_OPS,
        'orm_path':       'preferred_event__graceid',
        'needs_distinct': False,
        'help_text':      "Preferred event's GraceDB ID (e.g., G123456)",
    },
    'events': {
        'type':           'graceid',
        'operators':      ID_OPS,
        'orm_path':       'events__graceid',
        # Reverse FK: multiple event rows per superevent → requires distinct
        'needs_distinct': True,
        'help_text':      'Associated event graceid (e.g., G123456)',
    },
}

# ---------------------------------------------------------------------------
# Build final field schema dicts
# ---------------------------------------------------------------------------

_ATTR_FIELDS = _build_attr_fields()

EVENT_FIELDS = dict(_EVENT_CORE_FIELDS)
EVENT_FIELDS.update(_ATTR_FIELDS)

SUPEREVENT_FIELDS = dict(_SUPEREVENT_CORE_FIELDS)

FIELDS = {
    'event':      EVENT_FIELDS,
    'superevent': SUPEREVENT_FIELDS,
}

# ---------------------------------------------------------------------------
# Field aliases: alias → canonical field name
# Aliases are normalised during validation (before translation).
# ---------------------------------------------------------------------------

EVENT_ALIASES = {
    'graceid': 'id',
    'ifos':    'instruments',
}

SUPEREVENT_ALIASES = {
    'superevent_id': 'id',
    'gpstime':       't_0',
    'is_public':     'is_exposed',
    'event':         'events',
}

ALIASES = {
    'event':      EVENT_ALIASES,
    'superevent': SUPEREVENT_ALIASES,
}

# ---------------------------------------------------------------------------
# Accessor helpers
# ---------------------------------------------------------------------------

def normalize_field_name(field, object_type):
    """
    Return the schema key for *field* in *object_type*, or None if unknown.

    Attribute fields are stored under their canonical key (e.g., 'singleinspiral.snr').
    This function normalises any accepted input form to that key:
      - Top-level aliases:  'graceid' → 'id',  'gpstime' → 't_0'
      - Direct lookup:      'singleinspiral.snr' → 'singleinspiral.snr'
      - Short alias:        'si.snr'  → 'singleinspiral.snr'
      - Long alias:         'coincinspiral.mass' → 'coincinspiralevent.mass'

    For superevent queries, any valid event field can be accessed via the
    ``preferred_event.`` prefix, which is resolved by delegating the suffix
    to the event schema:
      - 'preferred_event.far'    → 'preferred_event.far'
      - 'preferred_event.si.snr' → 'preferred_event.singleinspiral.snr'
    The resulting canonical key is only meaningful to ``get_field_schema``;
    it is NOT a key in ``SUPEREVENT_FIELDS``.
    """
    aliases = ALIASES.get(object_type, {})
    field_schema = FIELDS.get(object_type, {})

    if field in aliases:
        return aliases[field]

    if field in field_schema:
        return field

    # preferred_event.FOO delegation (superevent queries only).
    # Must come before the generic dot-notation branch so that e.g.
    # 'preferred_event.far' is not misinterpreted as table 'preferred_event',
    # sub-field 'far' (which would not match any entry in SUPEREVENT_FIELDS).
    if object_type == 'superevent' and field.startswith('preferred_event.'):
        sub_field = field[len('preferred_event.'):]
        event_canonical = normalize_field_name(sub_field, 'event')
        if event_canonical is None:
            return None
        if event_canonical in _EXCLUDED_PREFERRED_EVENT_FIELDS:
            return None
        return f'preferred_event.{event_canonical}'

    # Dot-notation: resolve any table alias/short-form to the canonical table name
    if '.' in field:
        table_part, sub_field = field.split('.', 1)
        canonical_table = TABLE_ALIASES.get(table_part.lower(), table_part.lower())
        canonical_key = f'{canonical_table}.{sub_field}'
        if canonical_key in field_schema:
            return canonical_key

    return None


def get_field_schema(field, object_type):
    """
    Return the schema dict for *field* in *object_type*, or None if unknown.
    Always normalises the field name first.

    For superevent ``preferred_event.FOO`` canonicals, synthesises the schema
    on the fly by prefixing ORM paths from the event schema.
    """
    canonical = normalize_field_name(field, object_type)
    if canonical is None:
        return None

    # preferred_event.FOO delegation: synthesise schema from the event schema
    if object_type == 'superevent' and canonical.startswith('preferred_event.'):
        sub_canonical = canonical[len('preferred_event.'):]
        event_schema = FIELDS['event'].get(sub_canonical)
        if event_schema is None:
            return None
        return _make_preferred_event_schema(event_schema)

    return FIELDS.get(object_type, {}).get(canonical)
