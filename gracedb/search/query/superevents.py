from __future__ import absolute_import
import datetime
import logging
import pytz
import re
try:
    from functools import reduce
except ImportError:  # python < 3
    pass

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

from django.conf import settings
from django.db.models import Q
from django.db.models.query import QuerySet

from core.utils import letters_to_int, int_to_letters
# (weak) natural language time parsing.
from events.nltime import nlTimeExpression as nltime_
from superevents.models import Superevent
from .labels import getLabelQ
from ..constants import RUN_MAP, RUN_MAP_FLAT, ExpressionOperator
from ..utils import maybeRange, run_map_search_filter

from pyparsing import Word, nums, Literal, CaselessLiteral, delimitedList, \
    Suppress, QuotedString, Keyword, Combine, Or, Optional, OneOrMore, \
    ZeroOrMore, alphas, alphanums, Regex, opAssoc, \
    oneOf, stringStart,  stringEnd, FollowedBy, ParseResults, ParseException, \
    CaselessKeyword, pyparsing_common, tokenMap

# Set up logger
logger = logging.getLogger(__name__)


# Function for parsing matched superevent ID tokens
def parse_superevent_id(name, toks, filter_prefix=None):
    # Wildcard support: if wildcard is present, match all superevents starting with the parsed string
    if hasattr(toks, 'wildcard') and toks.wildcard == '*':
        s_id_prefix = toks.preprefix + toks.prefix + toks.date
        if hasattr(toks, 'suffix') and toks.suffix:
            s_id_prefix += toks.suffix
        f_kwargs = {
            '{}__startswith'.format('superevent_id' if not filter_prefix else filter_prefix + 'superevent_id'): s_id_prefix
        }
        fullQ = Q(**f_kwargs)
        return (name, fullQ)

    # If no suffix, add either 'a' or 'A' depending on GW status
    # This allows queries like GW150914 to match the first superevent
    # on that date
    if not hasattr(toks, 'suffix') or not toks.suffix:
        toks['suffix'] = int_to_letters(1)
        if (toks.prefix == Superevent.GW_ID_PREFIX):
            toks['suffix'] = toks.suffix.upper()

    # Allow flexible suffix capitalization
    if (toks.prefix == Superevent.GW_ID_PREFIX):
        toks['suffix'] = toks.suffix.upper()
    else:
        toks['suffix'] = toks.suffix.lower()

    # Combine into full ID and get lookup kwargs
    s_id = toks.preprefix + toks.prefix + toks.date + toks.suffix
    f_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup(s_id)

    # Add any necessary prefix. For example, if we want to look up events
    # that are part of a given superevent, we have to add the 'superevent__'
    # prefix to the filter kwargs.
    if filter_prefix:
        if not filter_prefix.endswith('__'):
            filter_prefix += '__'
        f_kwargs = {'{pref}{k}'.format(pref=filter_prefix, k=k): v for k,v in f_kwargs.items()}

    fullQ = Q(**f_kwargs)
    return (name, fullQ)



# Construct an expression for date-based superevent ids
superevent_preprefix = Optional(Or([CaselessLiteral(pref) for pref in
    [Superevent.SUPEREVENT_CATEGORY_TEST, Superevent.SUPEREVENT_CATEGORY_MDC]])
    ).setResultsName('preprefix')
# Allow S, MS, TS, GW as valid prefixes
superevent_prefix = Or([CaselessLiteral(pref) for pref in
    ('S', 'MS', 'TS', 'GW')]).setResultsName('prefix')
# Exact match: 6 digits
superevent_date_exact = Word(nums, exact=6).setResultsName('date')
superevent_suffix = Word(alphas).setResultsName('suffix')
# Wildcard match: 1+ digits, must end with '*'
superevent_date_flex = Word(nums, min=1).setResultsName('date')
superevent_wildcard = Literal('*').setResultsName('wildcard')
# Patterns
superevent_expr_wildcard = superevent_preprefix + superevent_prefix + superevent_date_flex + Optional(superevent_suffix) + superevent_wildcard
superevent_expr_exact = superevent_preprefix + superevent_prefix + superevent_date_exact + Optional(superevent_suffix)
# Prioritize wildcard pattern first
superevent_expr = (superevent_expr_wildcard | superevent_expr_exact)

# Dict of queryable parameters which are compiled into a pyparsing
# expression below
parameter_dicts = {
    # id: S180506a OR superevent_id: GWA180517 OR S180506a
    'superevent_id': {
        'keyword': ['id', 'superevent_id'],
        'keywordOptional': True,
        'value': superevent_expr,
        'doRange': False,
        'parseAction': lambda s, loc, toks: parse_superevent_id(
            "superevent_id", toks, filter_prefix=None),
    },
    # runid: O2 or O2
    'runid': {
        'keyword': 'runid',
        'keywordOptional': True,
        'value': Or(list(map(CaselessLiteral, RUN_MAP_FLAT))).setName(
            "run id"),
        'doRange': False,
        'parseAction': lambda toks: ("t_0", run_map_search_filter(toks[0], 't_0')),
    },
    # t_0: 123456.0987 OR gpstime: 123456.0987
    't_0': {
        'keyword': ['t_0', 'gpstime'],
        'keywordOptional': True,
        'value': pyparsing_common.number.copy(),
        'doRange': True,
        'parseAction': maybeRange('t_0'),
    },
    # t_start: 123456.0987
    't_start': {
        'keyword': 't_start',
        'keywordOptional': False,
        'value': pyparsing_common.number.copy(),
        'doRange': True,
        'parseAction': maybeRange('t_start'),
    },
    # t_end: 123456.0987
    't_end': {
        'keyword': 't_end',
        'keywordOptional': False,
        'value': pyparsing_common.number.copy(),
        'doRange': True,
        'parseAction': maybeRange('t_end'),
    },
    # "albert.einstein@ligo.org OR submitter: "albert.einstein@ligo.org"
    'submitter': {
        'keyword': 'submitter',
        'keywordOptional': True,
        'value': QuotedString('"'),
        'parseAction': lambda toks: ("submitter",
            Q(submitter__username__icontains=toks[0]) |
            Q(submitter__last_name__icontains=toks[0])),
    },
    # preferred_event: G123456, preferred_event: G1234 .. G2234
    'preferred_event': {
        'keyword': 'preferred_event',
        'keywordOptional': False,
        'value': Suppress(Word("GHMTghmt", exact=1)) + \
            Word(nums).setParseAction(tokenMap(int)),
        'doRange': True,
        'parseAction': maybeRange("preferred_event",
            dbname="preferred_event__id"),
    },
    # event: G1234, event: G1234 .. G2234
    'event': {
        'keyword': ['event', 'events'],
        'keywordOptional': False,
        'value': Suppress(Word("EGHMTeghmt", exact=1)) + \
            Word(nums).setParseAction(tokenMap(int)),
        'doRange': True,
        'parseAction': maybeRange("event", dbname="events__id"),
    },
    # is_gw: true|false (case-insensitive)
    'is_gw': {
        'keyword': 'is_gw',
        'keywordOptional': False,
        'value': Or([CaselessLiteral(b) for b in ['true', 'false']]),
        'parseAction': lambda toks: ("is_gw", Q(is_gw=(toks[0] == "true"))),
    },
    # is_public: true|false OR is_exposed: true|false
    'is_public': {
        'keyword': ['is_public', 'is_exposed'],
        'keywordOptional': False,
        'value': Or([CaselessLiteral(b) for b in ['true', 'false']]),
        'parseAction': lambda toks: ("is_exposed",
            Q(is_exposed=(toks[0] == "true"))),
    },
    # status: internal|public OR internal|public
    'public': {
        'keyword': 'status',
        'keywordOptional': True,
        'value': Or([CaselessLiteral(b) for b in ['public', 'internal']]),
        'parseAction': lambda toks: ("is_exposed",
            Q(is_exposed=(toks[0] == "public"))),
    },
    # created: yesterday .. now (uses events.nltime.nltimeExpression)
    'created_nl': {
        'keyword': 'created',
        'keywordOptional': True,
        'doRange': True,
        'value': nltime_.setParseAction(lambda toks: toks["calculatedTime"]),
        'parseAction': maybeRange("created"),
    },
    # created: YYYY-MM-DD HH:MM:SS (time = optional, can do range too)
    'created_dt': {
        'keyword': 'created',
        'keywordOptional': True,
        'doRange': True,
        'value': (Word(nums, exact=4) + Suppress('-') + \
            Word(nums, exact=2) + Suppress('-') + Word(nums, exact=2) + \
            Optional(Word(nums, exact=2) + Suppress(':') + \
            Word(nums, exact=2) + Optional(Suppress(':') + \
            Word(nums, exact=2)))).setParseAction(lambda toks:
            pytz.timezone(settings.TIME_ZONE).localize(
            datetime.datetime(*list(map(int, toks))))),
        'parseAction': maybeRange("created"),
    },
    # test OR category: test
    'category': {
        'keyword': 'category',
        'keywordOptional': True,
        'doRange': False,
        'value': Or([CaselessLiteral(t[1]) for t in
            Superevent.SUPEREVENT_CATEGORY_CHOICES]),
        'parseAction': lambda toks: ("category",
            Q(category=[t[0] for t in Superevent.SUPEREVENT_CATEGORY_CHOICES
              if t[1].lower()==toks[0].lower()][0])),
    },
    # far: 1e-5 SAME AS far == 1e-5. Other options like: far > 1e-5
    'far': {
        'doRange': False,
        'value': Suppress(CaselessLiteral('far')) + ExpressionOperator + \
            pyparsing_common.number.copy(),
        'parseAction': lambda toks: ("far",
            Q(**{'preferred_event__far' + toks[0]: toks[1]})),
    },
    # far in 1e-5, 1e-4 OR far: 1e-5 - 1e-4 OR far: 1e-5 .. 1e-4
    'far_range': {
        'doRange': False,
        'value': Suppress(CaselessLiteral('far')) + \
            Suppress(Or([CaselessLiteral(d) for d in ['in', ':']])) + \
            pyparsing_common.number.copy() + \
            Suppress(Or([CaselessLiteral(op) for op in [',', '..', '-']])) + \
            pyparsing_common.number.copy(),
        'parseAction': lambda toks: ("far_range",
            Q(**{'preferred_event__far__range': toks.asList()})),
    },
}

# Compile a list of expressions to try to match
expr_list = []
for k,p in parameter_dicts.items():

    # Define val and set name
    val = p['value']
    val.setName(k)

    # Add range with format: parameter .. parameter
    if p.get('doRange'):
        range_val = val + Suppress("..") + val
        val ^= range_val

    # Add keyword. Format is keyword: value
    if 'keyword' in p:
        if isinstance(p['keyword'], list):
            if p.get('keywordOptional'):
                keyword_list = [Optional(Suppress(Keyword(k + ":"))) for k in
                    p['keyword']]
            else:
                keyword_list = [Suppress(Keyword(k + ":")) for k in p['keyword']]
            keyword = reduce(lambda x,y: x^y, keyword_list)
        else:
            keyword = Suppress(Keyword(p['keyword'] + ":"))
            if p.get('keywordOptional'):
                keyword = Optional(keyword)

        # Combine keyword and value into a single expression
        expr = keyword + val
    else:
        expr = val

    # Set parse action
    expr = expr.setParseAction(p['parseAction'])

    # Append to list of all expressions
    expr_list.append(expr)

# Compile a combined expression by Or-ing all of the individual expressions
combined_expr = Or(expr_list)


def parseSupereventQuery(s):


    # Clean the label-related parts of the query out of the query string.
    labelQ = getLabelQ()
    s = labelQ.transformString(s)

    # A parser for the non-label-related remainder of the query string.
    q = combined_expr.setName("query term")

    # By default, queries don't return test or MDC superevents
    default_Q = ~Q(category=Superevent.SUPEREVENT_CATEGORY_TEST) & \
        ~Q(category=Superevent.SUPEREVENT_CATEGORY_MDC)

    # For an empty query, return default
    if not s:
        return default_Q

    try:
        # Match query string to parsers
        matches = (stringStart + OneOrMore(q) + stringEnd).parseString(s).asList()
    except ParseException as e:
        msg = str(e)
        allowed_prefixes = ['S', 'MS', 'TS', 'GW']

        # Mark this as a user input error to prevent Sentry reporting
        if sentry_sdk:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error_category", "user_input")
                scope.fingerprint = ["user-query-validation-error"]

                # Check for invalid wildcard (should be '*')
                if '*' not in s and any(w in s for w in ['?', '#', '%', '$']):
                    raise ValueError(f"Invalid wildcard in query: '{s}'. Only '*' is supported as a wildcard.")
                # Check for event-like grace ID (e.g., G0029)
                if re.match(r"^G\d+$", s.strip()):
                    raise ValueError(f"'{s}' looks like an event graceid. Only superevent IDs (S, MS, TS, GW) are valid in this search.")
                # Check for invalid prefix: look for a word at the start that is not in the allowed set
                m = re.match(r"([A-Za-z]+)\d{6,}\*?", s)
                if m and m.group(1) not in allowed_prefixes:
                    raise ValueError(f"Invalid superevent prefix in query: '{m.group(1)}'. Allowed prefixes are: {', '.join(allowed_prefixes)}.")
                # If the query doesn't match any known superevent or event pattern, give a clear error
                if not re.match(r"^(S|MS|TS|GW)\d{6,}([a-zA-Z]*)\*?$", s.strip()) and not re.match(r"^G\d+$", s.strip()):
                    raise ValueError(f"'{s}' is not a valid superevent ID or query. Valid superevent IDs start with S, MS, TS, or GW followed by a date and optional suffix. Example: S250908a or GW250908A.")
                # Check for invalid wildcard (should be '*')
                if '*' not in s and any(w in s for w in ['?', '#', '%', '$']):
                    raise ValueError(f"Invalid wildcard in query: '{s}'. Only '*' is supported as a wildcard.")
                # Fallback generic error
                raise ValueError(f"Invalid superevent query: '{s}'. {msg}")
        else:
            # If sentry_sdk is not available, just raise the errors normally
            # Check for invalid wildcard (should be '*')
            if '*' not in s and any(w in s for w in ['?', '#', '%', '$']):
                raise ValueError(f"Invalid wildcard in query: '{s}'. Only '*' is supported as a wildcard.")
            # Check for event-like grace ID (e.g., G0029)
            if re.match(r"^G\d+$", s.strip()):
                raise ValueError(f"'{s}' looks like an event graceid. Only superevent IDs (S, MS, TS, GW) are valid in this search.")
            # Check for invalid prefix: look for a word at the start that is not in the allowed set
            m = re.match(r"([A-Za-z]+)\d{6,}\*?", s)
            if m and m.group(1) not in allowed_prefixes:
                raise ValueError(f"Invalid superevent prefix in query: '{m.group(1)}'. Allowed prefixes are: {', '.join(allowed_prefixes)}.")
            # If the query doesn't match any known superevent or event pattern, give a clear error
            if not re.match(r"^(S|MS|TS|GW)\d{6,}([a-zA-Z]*)\*?$", s.strip()) and not re.match(r"^G\d+$", s.strip()):
                raise ValueError(f"'{s}' is not a valid superevent ID or query. Valid superevent IDs start with S, MS, TS, or GW followed by a date and optional suffix. Example: S250908a or GW250908A.")
            # Check for invalid wildcard (should be '*')
            if '*' not in s and any(w in s for w in ['?', '#', '%', '$']):
                raise ValueError(f"Invalid wildcard in query: '{s}'. Only '*' is supported as a wildcard.")
            # Fallback generic error
            raise ValueError(f"Invalid superevent query: '{s}'. {msg}")

    # Append default category query if category is not specified in the query
    # OR if a superevent ID is not directly specified in the query
    match_keys = [m[0] for m in matches]
    no_default_category_keys = ['category', 'superevent_id']
    if not any([k in match_keys for k in no_default_category_keys]):
        matches.append(('category', default_Q))

    return reduce(Q.__and__, [m[1] for m in matches], Q())
