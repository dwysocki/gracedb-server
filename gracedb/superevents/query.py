import datetime
import logging
import pytz

from django.db.models import Q
from django.db.models.query import QuerySet

from core.utils import letters_to_int
from events.models import Group, Pipeline, Search, Label
# (weak) natural language time parsing.
from events.nltime import nlTimeExpression as nltime_
from events.query_utils import maybeRange, getLabelQ, RUN_MAP
from .models import Superevent

from pyparsing import Word, nums, Literal, CaselessLiteral, delimitedList, \
    Suppress, QuotedString, Keyword, Combine, Or, Optional, OneOrMore, \
    ZeroOrMore, alphas, alphanums, Regex, opAssoc, operatorPrecedence, \
    oneOf, stringStart,  stringEnd, FollowedBy, ParseResults, ParseException, \
    CaselessKeyword

# Set up logger
logger = logging.getLogger(__name__)

# Function for parsing matched superevent ID tokens
def parse_superevent_id(name, toks, filter_prefix=None):
    # toks = matched superevent id

    # Get lookup kwargs and convert to a Q object
    f_kwargs = Superevent.get_filter_kwargs_for_date_id_lookup(toks)
    fullQ = Q(**f_kwargs)

    return (name, fullQ)

# Construct an expression for date-based superevent ids
superevent_preprefix = Optional(Or([CaselessLiteral(pref) for pref in
    [Superevent.SUPEREVENT_CATEGORY_TEST, Superevent.SUPEREVENT_CATEGORY_MDC]])
    )
superevent_prefix = Or([CaselessLiteral(pref) for pref in
    Superevent.DEFAULT_ID_PREFIX, Superevent.GW_ID_PREFIX])
superevent_date = Word(nums, exact=6)
superevent_suffix = Word(alphas)
superevent_expr = Combine(superevent_preprefix + superevent_prefix +
    superevent_date + superevent_suffix)

# Dict of queryable parameters which are compiled into a pyparsing
# expression below
parameter_dicts = {
    # id: S180506a OR superevent_id: GWA180517 OR S180506a
    'superevent_id': {
        'keyword': ['id', 'superevent_id'],
        'keywordOptional': True,
        'value': superevent_expr,
        'doRange': False,
        'parseAction': lambda toks: parse_superevent_id(
            "superevent_id", toks[0], filter_prefix=None),
    },
    # runid: O2 or O2
    'runid': {
        'keyword': 'runid',
        'keywordOptional': True,
        'value': Or(map(CaselessLiteral, RUN_MAP.keys())).setName("run id"),
        'doRange': False,
        'parseAction': lambda toks: ("t_0", Q(t_0__range=RUN_MAP[toks[0]])),
    },
    # t_0: 123456.0987 OR gpstime: 123456.0987
    't_0': {
        'keyword': ['t_0', 'gpstime'],
        'keywordOptional': True,
        'value': Word(nums+'.'),
        'doRange': True,
        'parseAction': maybeRange('t_0'),
    },
    # t_start: 123456.0987
    't_start': {
        'keyword': 't_start',
        'keywordOptional': False,
        'value': Word(nums+'.'),
        'doRange': True,
        'parseAction': maybeRange('t_start'),
    },
    # t_end: 123456.0987
    't_end': {
        'keyword': 't_end',
        'keywordOptional': False,
        'value': Word(nums+'.'),
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
            Q(submitter_last_name__icontains=toks[0])),
    },
    # preferred_event: G123456, preferred_event: G1234 .. G2234
    'preferred_event': {
        'keyword': 'preferred_event',
        'keywordOptional': False,
        'value': Suppress(Word("GHMTghmt", exact=1)) + Word(nums),
        'doRange': True,
        'parseAction': maybeRange("preferred_event",
            dbname="preferred_event__id"),
    },
    # event: G1234, event: G1234 .. G2234
    'event': {
        'keyword': 'event',
        'keywordOptional': False,
        'value': Suppress(Word("EGHMTeghmt", exact=1)) + Word(nums),
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
            pytz.utc.localize(datetime.datetime(*map(int, toks)))),
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
}


# Compile a list of expressions to try to match
expr_list = []
for k,p in parameter_dicts.iteritems():

    # Define val and set name
    val = p['value']
    val.setName(k)

    # Add keyword. Format is keyword: value
    if isinstance(p['keyword'], list):
        if p.has_key('keywordOptional') and p['keywordOptional']:
            keyword_list = [Optional(Suppress(Keyword(k + ":"))) for k in
                p['keyword']]
        else:
            keyword_list = [Suppress(Keyword(k + ":")) for k in p['keyword']]
        keyword = reduce(lambda x,y: x^y, keyword_list)
    else:
        keyword = Suppress(Keyword(p['keyword'] + ":"))
        if p.has_key('keywordOptional') and p['keywordOptional']:
            keyword = Optional(keyword)

    # Add range with format: parameter .. parameter
    if p.has_key('doRange') and p['doRange']:
        range_val = val + Suppress("..") + val
        val ^= range_val

    # Combine keyword and value into a single expression
    full_expr = keyword + val

    # Set parse action
    full_expr = full_expr.setParseAction(p['parseAction'])

    # Append to list of all expressions
    expr_list.append(full_expr)

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

    # Match query string to parsers
    matches = (stringStart + OneOrMore(q) + stringEnd).parseString(s).asList()

    # Append default category query if category is not specified in the query
    if 'category' not in [m[0] for m in matches]:
        matches.append(('category', default_Q))

    return reduce(Q.__and__, [m[1] for m in matches], Q())

