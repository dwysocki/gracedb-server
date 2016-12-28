
#   nifos: INTEGER
#   [ifo:] IFO[,IFO]*
# . [group:] GROUP[|GROUP]*
# . [type:] TYPE[|TYPE]*
# . [gid:] GID[..GID]
#   [date:] DATE[..DATE]
# . [gpstime:] GPSTIME[..GPSTIME]
# ~ [label:] LABEL[|LABEL]
# ~ [label:] LABEL[,LABEL]

#import pyparsing as p

# (weak) natural language time parsing.
from nltime import nlTimeExpression as nltime_
nltime = nltime_.setParseAction(lambda toks: toks["calculatedTime"])

#import time, datetime
import datetime
import models
from django.db.models import Q
from django.db.models.query import QuerySet
import pytz

from pyparsing import Word, nums, Literal, CaselessLiteral, delimitedList, \
    Suppress, QuotedString, Keyword, Combine, Or, Optional, OneOrMore, \
    ZeroOrMore, alphas, alphanums, Regex, opAssoc, operatorPrecedence, \
    oneOf, stringStart,  stringEnd, FollowedBy, ParseResults, ParseException, \
    CaselessKeyword

def maybeRange(name, dbname=None):
    dbname = dbname or name
    def f(toks):
        if len(toks) == 1:
            return name, Q(**{dbname: toks[0]})
        return name, Q(**{dbname+"__range": toks.asList()})
    return f

#encodeType = dict(
#    [(x[1],x[0]) for x in models.Event.ANALYSIS_TYPE_CHOICES] +
#    [(x[0],x[0]) for x in models.Event.ANALYSIS_TYPE_CHOICES]
#    )

#def doType(toks):
#    return ("type", Q(analysisType__in=[encodeType[tok] for tok in toks]))

def convertToGps(dateStr):
    return 12

def doDate(toks):
    if len(toks) == 1:
        return "gpstime", Q("gpstime", convertToGps(toks[0]))
    return "gpstime", Q("gpstime__range", map(convertToGps(toks.toList())))

# hasfar flag
hasfarQ = CaselessLiteral("hasfar")
hasfarQ.setParseAction(lambda toks: ("hasfar", Q(far__isnull=False)))

# GPS Times
gpstime = Word(nums+'.').setName("GPS time")
gpstimeRange = (gpstime + Suppress("..") + gpstime).setName("GPS time range")

gpsQ = Optional(Suppress(Keyword("gpstime:"))) + (gpstime^gpstimeRange)
gpsQ = gpsQ.setParseAction(maybeRange("gpstime"))

# run ids
runmap = {
    # Nov 30 16:00:00 UTC 2016 - ?
    # (end date currently set to Apr 1 00:00:00 UTC 2017) (TP's guess)
    "O2A" :     (1164556817, 1175040018),
    # Friday, Sept 18th, 10 AM CDT - Tuesday, Jan 12th, 10:00 AM CST
    "O1"  :     (1126623617, 1136649617),
    # Monday, Aug 17th, 10 AM CDT - Friday, Sept 18th, 10 AM CDT 
    "ER8" :     (1123858817, 1126623617),
    # Jun 03 21:00:00 UTC 2015 - Jun 14 15:00:00 UTC 2015
    "ER7" :     (1117400416, 1118329216),
    # Dec 08 16:00:00 UTC 2014 - Dec 17 15:00:00 UTC 2014
    "ER6" :     (1102089616, 1102863616),
    # Jan 15 12:00:00 UTC 2014 - Mar 15 2014 00:00:00 UTC
    "ER5" :     (1073822416, 1078876816),
    # Jul 15 00:00:00 UTC 2013 - Aug 30 2013 00:00:00 UTC
    "ER4" :     (1057881616, 1061856016),
    # Feb 5 16:00:00 CST 2013 - Mon Feb 25 00:00:00 GMT 2013
    "ER3" :     (1044136816, 1045785616),
    # Jul 18 17:00:00 GMT 2012 - Aug 8 17:00:00 GMT 2012
    "ER2" : (1026666016, 1028480416),
    #"ER2" : (1026061216, 1028480416),
    #"ER2" : (1026069984, 1028480416),  # soft start
    "ER1":  (1011601640, 1013299215),
    "ER1test": (1010944815, 1011601640),  # Pre ER1
    "S6"  : (931035296, 971622087),
    "S6A" : (931035296, 935798487),
    "S6B" : (937800015, 947260815),
    "S6C" : (949449543, 961545687),
    "S6D" : (956707143, 971622087),
}
runid = Or(map(CaselessLiteral, runmap.keys())).setName("run id")
#runidList = OneOrMore(runid).setName("run id list")
runQ = (Optional(Suppress(Keyword("runid:"))) + runid)
runQ = runQ.setParseAction(lambda toks: ("gpstime", Q(gpstime__range=
                                                        runmap[toks[0]])))

# Analysis Groups
# XXX Querying the database at module compile time is a bad idea!
# See: https://docs.djangoproject.com/en/1.8/topics/testing/overview/
groupNames = [group.name for group in models.Group.objects.all()]
group = Or(map(CaselessLiteral, groupNames)).setName("analysis group name")
#groupList = delimitedList(group, delim='|').setName("analysis group list")
groupList = OneOrMore(group).setName("analysis group list")
groupQ = (Optional(Suppress(Keyword("group:"))) + groupList)
groupQ = groupQ.setParseAction(lambda toks: ("group",
                                             Q(group__name__in=toks.asList())))

# Pipeline
pipelineNames = [pipeline.name for pipeline in models.Pipeline.objects.all()]
pipeline = Or(map(CaselessLiteral, pipelineNames)).setName("pipeline name")
pipelineList = OneOrMore(pipeline).setName("pipeline list")
pipelineQ = (Optional(Suppress(Keyword("pipeline:"))) + pipelineList)
pipelineQ = pipelineQ.setParseAction(lambda toks: ("pipeline",
                                     Q(pipeline__name__in=toks.asList())))

# Search
searchNames = [search.name for search in models.Search.objects.all()]
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
                                 ("search", Q(search__name__in=toks.asList()))
                                )

# Gracedb ID
gid = Suppress(Word("gG", max=1)) + Word("0123456789")
gidRange = gid + Suppress("..") + gid
gidQ = Optional(Suppress(Keyword("gid:"))) + (gid^gidRange)
gidQ = gidQ.setParseAction(maybeRange("gid", dbname="id"))

# hardware injection id
hid = Suppress(Word("hH", max=1)) + Word("0123456789")
hidRange = hid + Suppress("..") + hid
hidQ = Optional(Suppress(Keyword("hid:"))) + (hid^hidRange)
hidQ = hidQ.setParseAction(maybeRange("hid", dbname="id"))

# test event id
tid = Suppress(Word("tT", max=1)) + Word("0123456789")
tidRange = tid + Suppress("..") + tid
tidQ = Optional(Suppress(Keyword("tid:"))) + (tid^tidRange)
tidQ = tidQ.setParseAction(maybeRange("tid", dbname="id"))

# External trigger event id
eid = Suppress(Word("eE", max=1)) + Word("0123456789")
eidRange = eid + Suppress("..") + eid
eidQ = Optional(Suppress(Keyword("eid:"))) + (eid^eidRange)
eidQ = eidQ.setParseAction(maybeRange("eid", dbname="id"))

# MDC event id
mid = Suppress(Word("mM", max=1)) + Word("0123456789")
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
#labelNames = [l.name for l in models.Label.objects.all()]
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

exprOperators = { "<" :  "__lt",
                  "<=":  "__lte",
                  "=" :  "",
                  ":" :  "",
                  ">" :  "__gt",
                  ">=":  "__gte",
                }

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

op = Or(map(Literal, exprOperators.keys()))
op.setParseAction(lambda toks: exprOperators[toks[0]])

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

###########################

#andTheseTags = ["attr"]
andTheseTags = ["nevents"]

#--------------------------------------------------------------------------
# parseQuery now handles all search terms *except* for the labels.
# The labels have to be handled separately, in filter_for_labels.
#--------------------------------------------------------------------------
def parseQuery(s):
    # labelQ is defined inside in order to avoid a compile-time database query
    # to get the label names.
    # Note the parse action for labelQ: Replace all tokens with the empty
    # string. This basically has the effect of removing any label query terms
    # from the query string.
    labelNames = [l.name for l in models.Label.objects.all()]
    #label = Or([CaselessLiteral(n) for n in labelNames]).\
    label = Or([CaselessKeyword(n) for n in labelNames]).\
            setParseAction( lambda toks: Q(labels__name=toks[0]) )
    andop   = oneOf(", &")
    orop    = Literal("|")
    minusop = oneOf("- ~")
    op = Or([andop,orop,minusop])
    oplabel = OneOrMore(op) + label
    labelQ_ = Optional(minusop) + label + ZeroOrMore(oplabel)
    labelQ = (Optional(Suppress(Keyword("label:"))) + labelQ_.copy())
    labelQ.setParseAction(lambda toks: '')

    # Clean the label-related parts of the query out of the query string.
    s = labelQ.transformString(s)

    # A parser for the non-label-related remainder of the query string.
    q = (ifoQ | hasfarQ | gidQ | hidQ | tidQ | eidQ | midQ | searchQ 
         | pipelineQ | groupQ | gpsQ | createdQ | submitterQ | runQ
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

#--------------------------------------------------------------------------
# Given a query string, separate out the label-related part, and return it
# as a list of Q objects and separators.
#--------------------------------------------------------------------------
def labelQuery(s, names=False):
    labelNames = [l.name for l in models.Label.objects.all()]
    #label = Or([CaselessLiteral(n) for n in labelNames])
    label = Or([CaselessKeyword(n) for n in labelNames])
    # If the filter objects are going to be applied to Lable 
    # objects to retrieve labels by name, names = True.
    # This is useful for the label query in userprofile.models.Trigger
    if names:
        label.setParseAction( lambda toks: Q(name=toks[0]) )
    else:
        label.setParseAction( lambda toks: Q(labels__name=toks[0]) )
    andop   = oneOf(", &")
    orop    = Literal("|")
    minusop = oneOf("- ~")
    op = Or([andop,orop,minusop])
    oplabel = OneOrMore(op) + label
    labelQ_ = Optional(minusop) + label + ZeroOrMore(oplabel)
    labelQ = (Optional(Suppress(Keyword("label:"))) + labelQ_.copy())
    toks = labelQ.searchString(s).asList()
    # This list will have either 1 or 0 elements.
    if len(toks):
        return toks[0]
    return toks

# The following version is used only for validation. Just to check that
# the query strictly conforms to the requirements of a label query.
def parseLabelQuery(s):
    labelNames = [l.name for l in models.Label.objects.all()]
    #label = Or([CaselessLiteral(n) for n in labelNames])
    label = Or([CaselessKeyword(n) for n in labelNames])
    andop   = oneOf(", &")
    orop    = Literal("|")
    minusop = oneOf("- ~")
    op = Or([andop,orop,minusop])
    oplabel = OneOrMore(op) + label
    labelQ_ = Optional(minusop) + label + ZeroOrMore(oplabel)
    labelQ = (Optional(Suppress(Keyword("label:"))) + labelQ_.copy())
    return labelQ.parseString(s).asList()

#--------------------------------------------------------------------------
# Given a list of the tokens, go through the list until you hit an AND or
# OR operator. Then apply the operator to the two surrounding query sets
# and send back a new list. The list will be shorter by 2 elements, since
# 'QuerySet, op, QuerySet' has been replaced by a single QuerySet.
#--------------------------------------------------------------------------
def handle_binary_ops(toks, op="or"):

    # Find the indices of the relevant operators.
    if op == "or":
        indices = [i for i, x in enumerate(toks) if x is '|']
    elif op == "and":
        indices = [i for i, x in enumerate(toks) if x == '&' or x==',']
    else:
        raise ValueError("Unknown operator")

    if len(indices) > 0:
        # Found the operator we're looking for
        updated = True
        i = indices[0]  # index of the first operator in the list
        leftQS = toks[i-1]
        rightQS = toks[i+1]

        # Check. The list items surrounding our operator need to be QuerySets
        if (not isinstance(leftQS, QuerySet)
            or not isinstance(rightQS, QuerySet)):
            raise ValueError("problem with query. Orphaned operator?")

        # Combine the two QuerySets
        if op=="or":
            outputQ = leftQS | rightQS
        elif op=="and":
            outputQ = leftQS & rightQS

        # Build up the new list of tokens to return. 
        new_toks = []
        for j in range(len(toks)):
            if j == i-1:
                new_toks.append(outputQ)
            elif j==i or j==i+1:
                continue
            else:
                new_toks.append(toks[j])

    else:
        # No such operator found, return the list of tokens unmodified.
        updated = False
        new_toks = toks

    return new_toks, updated

#--------------------------------------------------------------------------
# Given a queryset and a queryString (which may contain label search terms),
# filter the queryset for those label terms.
#--------------------------------------------------------------------------
def filter_for_labels(qs, queryString):
    if not queryString or len(queryString)==0:
        return qs

    # Parse the label part of the query string into its individual tokens.
    toks = labelQuery(queryString)
    if len(toks)==0:
        return qs

    # Handle the NOTs first.
    not_indices = [i for i, x in enumerate(toks) if x == '~' or x=='-']
    for i in not_indices:
        if not isinstance(toks[i+1], Q):
            raise ValueError("NOT operator should precede a Label name."
                             " Bad Query.")
        toks[i+1] = ~toks[i+1]

    # Now that we've applied the NOTs, remove them from the list
    toks = [x for x in toks if x not in ['-','~']]
        
    # Now the list of tokens consists of filter objects and separators. 
    # So next, we replace the filters with filtered querysets.
    toks = [ qs.filter(f) if isinstance(f,Q) else f for f in toks ]
        
    # Handle the ORs. We take the union of all QuerySets separated by 
    # OR operators.
    updated = True
    while updated:
        toks, updated = handle_binary_ops(toks,"or")

    # Handle the ANDs. Same kinda thang.
    updated = True
    while updated:
        toks, updated = handle_binary_ops(toks,"and")

    # By this time, the list of tokens should be down to a single QuerySet.
    if len(toks)>1:
        raise ValueError("The label query didn't reduce properly.")

    return toks[0]
