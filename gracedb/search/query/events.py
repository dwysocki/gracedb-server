#   nifos: INTEGER
#   [ifo:] IFO[,IFO]*
# . [group:] GROUP[|GROUP]*
# . [type:] TYPE[|TYPE]*
# . [gid:] GID[..GID]
#   [date:] DATE[..DATE]
# . [gpstime:] GPSTIME[..GPSTIME]
# ~ [label:] LABEL[|LABEL]
# ~ [label:] LABEL[,LABEL]
from __future__ import absolute_import
import datetime
from pyparsing import Word, nums, Literal, CaselessLiteral, delimitedList, \
    Suppress, QuotedString, Keyword, Combine, Or, Optional, OneOrMore, \
    ZeroOrMore, alphas, alphanums, Regex, opAssoc, operatorPrecedence, \
    oneOf, stringStart,  stringEnd, FollowedBy, ParseResults, ParseException, \
    CaselessKeyword
import pytz

from django.db.models import Q
from django.db.models.query import QuerySet

# (weak) natural language time parsing.
from events.nltime import nlTimeExpression as nltime_
nltime = nltime_.setParseAction(lambda toks: toks["calculatedTime"])
from events.models import Group, Pipeline, Search, Label
from .labels import getLabelQ
from .superevents import parse_superevent_id, superevent_expr
from ..constants import RUN_MAP, EXPR_OPERATORS
from ..utils import maybeRange


# hasfar flag
hasfarQ = CaselessLiteral("hasfar")
hasfarQ.setParseAction(lambda toks: ("hasfar", Q(far__isnull=False)))

# GPS Times
gpstime = Word(nums+'.').setName("GPS time")
gpstimeRange = (gpstime + Suppress("..") + gpstime).setName("GPS time range")

gpsQ = Optional(Suppress(Keyword("gpstime:"))) + (gpstime^gpstimeRange)
gpsQ = gpsQ.setParseAction(maybeRange("gpstime"))

# run ids
runid = Or(map(CaselessLiteral, RUN_MAP.keys())).setName("run id")
#runidList = OneOrMore(runid).setName("run id list")
runQ = (Optional(Suppress(Keyword("runid:"))) + runid)
runQ = runQ.setParseAction(lambda toks: ("gpstime", Q(gpstime__range=
                                                        RUN_MAP[toks[0]])))

# Gracedb ID
gid = Suppress(Word("gG", exact=1)) + Word("0123456789")
gidRange = gid + Suppress("..") + gid
gidQ = Optional(Suppress(Keyword("gid:"))) + (gid^gidRange)
gidQ = gidQ.setParseAction(maybeRange("gid", dbname="id"))

# hardware injection id
hid = Suppress(Word("hH", exact=1)) + Word("0123456789")
hidRange = hid + Suppress("..") + hid
hidQ = Optional(Suppress(Keyword("hid:"))) + (hid^hidRange)
hidQ = hidQ.setParseAction(maybeRange("hid", dbname="id"))

# test event id
tid = Suppress(Word("tT", exact=1)) + Word("0123456789")
tidRange = tid + Suppress("..") + tid
tidQ = Optional(Suppress(Keyword("tid:"))) + (tid^tidRange)
tidQ = tidQ.setParseAction(maybeRange("tid", dbname="id"))

# External trigger event id
eid = Suppress(Word("eE", exact=1)) + Word("0123456789")
eidRange = eid + Suppress("..") + eid
eidQ = Optional(Suppress(Keyword("eid:"))) + (eid^eidRange)
eidQ = eidQ.setParseAction(maybeRange("eid", dbname="id"))

# MDC event id
mid = Suppress(Word("mM", exact=1)) + Word("0123456789")
midRange = mid + Suppress("..") + mid
midQ = Optional(Suppress(Keyword("mid:"))) + (mid^midRange)
midQ = midQ.setParseAction(maybeRange("mid", dbname="id"))

# Submitter
# 6 Dec. 2016: Tanner and Alex added icontains functionality for submitter,
# in order to enable simpler search patterns. For more specific searches, users
# will have to use more complex search patterns. Last name matching
# functionality is primarily for searching for robot users.
submitter = QuotedString('"').setParseAction(lambda toks:
    Q(submitter__username__icontains=toks[0])
    | Q(submitter__last_name__icontains=toks[0])
)
submitterQ = Optional(Suppress(Keyword("submitter:"))) + submitter
submitterQ = submitterQ.setParseAction(lambda toks: ("submitter", toks[0]))

# Created times

nltimeRange = nltime + Suppress("..") + nltime

def doTime(tok):
    x = datetime.datetime(*(map(int, tok)))
    return pytz.utc.localize(x)

dash = Suppress('-')
colon = Suppress(':')
date_ = Regex(r'\d{4}') + dash +  Regex(r'\d{2}') + dash +  Regex(r'\d{2}')
dt = date_ + Optional(Regex(r'\d{2}')+colon+Regex(r'\d{2}')+
                Optional(colon+Regex(r'\d{2}')))
dt.setParseAction(doTime)

dtrange = dt + Suppress("..") + dt

createdQ = Optional(Suppress(Keyword("created:"))) \
    + (nltime^nltimeRange^dt^dtrange)
createdQ = createdQ.setParseAction(maybeRange("created"))

# Labels
# NOTE: The label query has been moved inside the parseQuery call to avoid
# database access at compile time (to get the list of label names).
# NOTE ALSO: This is an old attempt by Brian to get a more complex label logic
# search working. It worked for some searches, but not all. That's because, 
# the method below creates a composite Q object that is applied to each 
# *individiual* Event, label relationship. So if you search for
#
# EM_READY & ADVOK
#
# The search will not work correctly since it will look for an event with
# a label such that the label is named EM_READY and ADVOK. No single label
# will have both names. filter_for_labels below avoids this problem by applying
# each label Q filter and combining the resulting querysets as appropriate.
#
#labelNames = [l.name for l in Label.objects.all()]
#label = Or([CaselessLiteral(n) for n in labelNames]).\
#        setParseAction( lambda toks: Q(labels__name=toks[0]) )
#
#andop   = oneOf(", &").suppress()
#orop    = Literal("|").suppress()
#minusop = oneOf("- ~").suppress()
#
#labelQ_ = operatorPrecedence(label,
#    [(minusop, 1, opAssoc.RIGHT, lambda a,b,toks: ~toks[0][0]),
#     (orop,    2, opAssoc.LEFT,
#        lambda a,b,toks: reduce(Q.__or__, toks[0].asList(), Q())),
#     (andop,   2, opAssoc.LEFT,
#        lambda a,b,toks: reduce(Q.__and__, toks[0].asList(), Q())),
#    ]).setParseAction(lambda toks: toks[0])
#
#labelQ = (Optional(Suppress(Keyword("label:"))) + labelQ_.copy())
#labelQ.setParseAction(lambda toks: ("label", toks[0]))

###########################
# Query on event attributes

lparen = Suppress('(')
rparen = Suppress(')')

tableTranslations = {
        'si': 'singleinspiral',
        'ci': 'coincinspiralevent',
        'mb': 'multiburstevent',
        'li': 'lalinferenceburstevent',
        'coincinspiral': 'coincinspiralevent',
        'multiburst': 'multiburstevent',
        'grb': 'grbevent',
        'inj': 'siminspiralevent',
        }

def buildDjangoQueryField(toks):
    toks = [name.lower() for name in toks]
    return "__".join([tableTranslations.get(name, name) for name in toks])

exponent = Combine(Word("Ee") + Optional(Word("+-"))+Word(nums))

afloat = Combine(
           Word(nums) +
           Optional(Combine(Literal(".") + Word(nums)))
         ) + Optional(exponent)
afloat.setParseAction(lambda toks: float("".join(toks)))

#lhs = delimitedList(Word(alphas+'_'), '.')
lhs = delimitedList(Word(alphanums+'_'), '.')
lhs.setParseAction(buildDjangoQueryField)
rhs = afloat | QuotedString('"')

op = Or(map(Literal, EXPR_OPERATORS.keys()))
op.setParseAction(lambda toks: EXPR_OPERATORS[toks[0]])

simpleTerm = lhs + op + rhs
simpleTerm.setParseAction(lambda toks: Q(**{toks[0]+toks[1]: toks[2]}))

rangeTerm = lhs + Suppress('in') + rhs + Suppress(",") + rhs
rangeTerm.setParseAction(lambda toks: Q(**{toks[0]+"__range": toks[1:]}))

term = simpleTerm | rangeTerm

andop   = oneOf(", &").suppress()
orop    = Literal("|").suppress()
minusop = oneOf("- ~").suppress()

attrExpressions = operatorPrecedence(term,
    [(minusop, 1, opAssoc.RIGHT, lambda a,b,toks: ~toks[0][0]),
     (orop,    2, opAssoc.LEFT,
        lambda a,b,toks: reduce(Q.__or__, toks[0].asList(), Q())),
     (andop,   2, opAssoc.LEFT,
        lambda a,b,toks: reduce(Q.__and__, toks[0].asList(), Q())),
    ]).setParseAction(lambda toks: toks[0])

#attributeQ = lparen + attrExpressions + rparen
attributeQ = attrExpressions.copy()
attributeQ.setParseAction(lambda toks: ("attr", toks[0]))

###########################

ifoList = Regex(r'(L1|H1|H2|V1)(,(L1|H1|H2|V1))*')
ifoList.setParseAction(lambda toks: ("ifos", Q(instruments__contains=toks[0])))

# 12/28/2016 (TP): may be useful for future
#ifoList = Regex(r'(L1|H1|H2|V1)(,(L1|H1|H2|V1))*')
#ifoList.setParseAction(lambda toks: ("ifos", reduce(Q.__and__,
#    [Q(instruments__contains=ifo) for ifo in toks[0].split(',')])))

ifoListQ = Optional(Suppress(Keyword("ifos:"))) + ifoList

nifoQ = Suppress(Keyword("nevents:")) + Word(nums)
nifoQ.setParseAction(lambda toks: ("nevents", Q(nevents=toks[0])))

ifoQ = ifoListQ | nifoQ

# Superevent queries ---------------------------------------------------------

# Event is part of a superevent?
t_or_f = Or([CaselessLiteral(b) for b in ['true', 'false']])
inSupereventQ = Suppress(Keyword("in_superevent:")) + t_or_f
inSupereventQ = inSupereventQ.setParseAction(lambda toks: ("in_superevent",
    Q(superevent__isnull=(toks[0] == "false"))))

# Event is preferred for some superevent?
isPreferredEventQ = Suppress(Keyword("is_preferred_event:")) + t_or_f
isPreferredEventQ = isPreferredEventQ.setParseAction(lambda toks:
    ("is_preferred_event", Q(superevent_preferred_for__isnull=
    (toks[0] == "false"))))

# Event is part of a specific superevent?
supereventQ = Suppress(Keyword("superevent:")) + superevent_expr
supereventQ.setParseAction(lambda toks: parse_superevent_id(
    "superevent", toks, filter_prefix="superevent"))

###########################

#andTheseTags = ["attr"]
andTheseTags = ["nevents"]

#--------------------------------------------------------------------------
# parseQuery now handles all search terms *except* for the labels.
# The labels have to be handled separately, in filter_for_labels.
#--------------------------------------------------------------------------
def parseQuery(s):
    # Analysis Groups
    # XXX Querying the database at module compile time is a bad idea!
    # See: https://docs.djangoproject.com/en/1.8/topics/testing/overview/
    groupNames = [group.name for group in Group.objects.all()]
    group = Or(map(CaselessLiteral, groupNames)).setName("analysis group name")
    #groupList = delimitedList(group, delim='|').setName("analysis group list")
    groupList = OneOrMore(group).setName("analysis group list")
    groupQ = (Optional(Suppress(Keyword("group:"))) + groupList)
    groupQ = groupQ.setParseAction(lambda toks: ("group",
        Q(group__name__in=toks.asList())))

    # Pipeline
    pipelineNames = [pipeline.name for pipeline in Pipeline.objects.all()]
    pipeline = Or(map(CaselessLiteral, pipelineNames)).setName("pipeline name")
    pipelineList = OneOrMore(pipeline).setName("pipeline list")
    pipelineQ = (Optional(Suppress(Keyword("pipeline:"))) + pipelineList)
    pipelineQ = pipelineQ.setParseAction(lambda toks: ("pipeline",
        Q(pipeline__name__in=toks.asList())))

    # Search
    searchNames = [search.name for search in Search.objects.all()]
    search = Or(map(CaselessLiteral, searchNames)).setName("search name")
    # XXX Branson: The change below was made 2/17/15 to fix a bug in which 
    # searches like 'grbevent.ra > 0' failed due to the 'grb' being peeled off
    # and assumed to be part of a 'Search' query. So we don't consume a token
    # for the search query if it is immediately followed by the caseless 
    # literal 'event'.
    eventLiteral = CaselessLiteral('event')
    #searchList = OneOrMore(search).setName("search list")
    searchList = OneOrMore(search + ~FollowedBy(eventLiteral)) \
        .setName("search list")
    searchQ = (Optional(Suppress(Keyword("search:"))) + searchList)
    searchQ = searchQ.setParseAction(lambda toks:
        ("search", Q(search__name__in=toks.asList())))

    # Get labelQ
    labelQ = getLabelQ()

    # Clean the label-related parts of the query out of the query string.
    s = labelQ.transformString(s)

    # A parser for the non-label-related remainder of the query string.
    q = (ifoQ | hasfarQ | gidQ | hidQ | tidQ | eidQ | midQ | searchQ 
         | pipelineQ | groupQ | gpsQ | createdQ | submitterQ | runQ
         | inSupereventQ | supereventQ | isPreferredEventQ
         | attributeQ
        ).setName("query term")

    d={}
    if not s:
        # Empty query return everything not in Test group
        # and not in the MDC group
        return ~Q(group__name="Test") & ~Q(search__name="MDC")
    for (tag, qval) in (stringStart + OneOrMore(q) + stringEnd) \
                        .parseString(s).asList():
        if tag in andTheseTags:
            d[tag] = d.get(tag,Q()) & qval
        else:
            d[tag] = d.get(tag,Q()) | qval
    #if s.find("Test") < 0 and "tid" not in d:
    if s.lower().find("test") < 0 and "tid" not in d:
        # If Test group is not mentioned in the query, we exclude it.
        if "group" in d:
            d["group"] &= ~Q(group__name="Test")
        else:
            d["group"] = ~Q(group__name="Test")
    if s.lower().find("mdc") < 0 and "mid" not in d:
        # If MDC search is not mentioned in the query, we exclude it.
        if "search" in d:
            d["search"] &= ~Q(search__name="MDC")
        else:
            d["search"] = ~Q(search__name="MDC")
    if "tid" in d:
        d["tid"] = d["tid"] & Q(group__name="Test")
    if "hid" in d:
        d["hid"] = d["hid"] & Q(pipeline__name="HardwareInjection")
    if "eid" in d:
        d["eid"] = d["eid"] & Q(group__name="External")
    if "mid" in d:
        d["mid"] = d["mid"] & Q(search__name="MDC")
    if "id" in d:
        d["id"] = d["id"] & ~Q(pipeline__name="HardwareInjection") \
                  & ~Q(group__name="External")
    if "id" in d and "hid" in d:
        d["id"] = d["id"] | d["hid"]
        del d["hid"]
    return reduce(Q.__and__, d.values(), Q())
