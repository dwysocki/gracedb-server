
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

import time, datetime
import models
from django.db.models import Q

from pyparsing import \
    Word, nums, Literal, CaselessLiteral, delimitedList, Suppress, QuotedString, \
    Keyword, Combine, Or, Optional, OneOrMore, alphas, Regex, \
    opAssoc, operatorPrecedence, oneOf, \
    stringStart, stringEnd, ParseException

def maybeRange(name, dbname=None):
    dbname = dbname or name
    def f(toks):
        if len(toks) == 1:
            return name, Q(**{dbname: toks[0]})
        return name, Q(**{dbname+"__range": toks.asList()})
    return f

encodeType = dict(
    [(x[1],x[0]) for x in models.Event.ANALYSIS_TYPE_CHOICES] +
    [(x[0],x[0]) for x in models.Event.ANALYSIS_TYPE_CHOICES]
    )

def doType(toks):
    return ("type", Q(analysisType__in=[encodeType[tok] for tok in toks]))

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
gpstime = Word(nums).setName("GPS time")
gpstimeRange = (gpstime + Suppress("..") + gpstime).setName("GPS time range")

gpsQ = Optional(Suppress(Keyword("gpstime:"))) + (gpstime^gpstimeRange)
gpsQ = gpsQ.setParseAction(maybeRange("gpstime"))

# run ids
runmap = {
   "ER3" : (1044136816, 1045785616),  # Feb 5 16:00:00 CST 2013 - Mon Feb 25 00:00:00 GMT 2013
   #"ER2" : (1026061216, 1028480416),
   #"ER2" : (1026069984, 1028480416),  # soft start
    "ER2" : (1026666016, 1028480416),  # Jul 18 17:00:00 GMT 2012 - Aug 8 17:00:00 GMT 2012
    "ER1" : (1010880015, 1100000000),  # End time is very wrong.
    "S6"  : (931035296, 971622087),
    "S6A" : (931035296, 935798487),
    "S6B" : (937800015, 947260815),
    "S6C" : (949449543, 961545687),
    "S6D" : (956707143, 971622087),
}
runid = Or(map(CaselessLiteral, runmap.keys())).setName("run id")
#runidList = OneOrMore(runid).setName("run id list")
runQ = (Optional(Suppress(Keyword("runid:"))) + runid)
runQ = runQ.setParseAction(lambda toks: ("gpstime", Q(gpstime__range=runmap[toks[0]])))
                          #lambda toks: ("gpstime", Q("gpstime__range": runmap[toks[0]])) )

# Analysis Groups
groupNames = [group.name for group in models.Group.objects.all()]
group = Or(map(CaselessLiteral, groupNames)).setName("analysis group name")
#groupList = delimitedList(group, delim='|').setName("analysis group list")
groupList = OneOrMore(group).setName("analysis group list")
groupQ = (Optional(Suppress(Keyword("group:"))) + groupList)
groupQ = groupQ.setParseAction(lambda toks: ("group", Q(group__name__in=toks.asList())))


# Analysis Types
atypeNames = encodeType.keys()
atype = Or(map(CaselessLiteral, atypeNames))
atypeList = delimitedList(atype, delim='|').\
            setName("analylsis type list").\
            setResultsName("atypes")
atypeQ = (Optional(Suppress(Keyword("type:"))) + atypeList).\
            setParseAction(doType)

# Gracedb ID
gid = Suppress("G")+Word("0123456789")
gidRange = gid + Suppress("..") + gid
gidQ = Optional(Suppress(Keyword("gid:"))) + (gid^gidRange)
gidQ = gidQ.setParseAction(maybeRange("id"))

# hardware injection id
hid = Suppress("H")+Word("0123456789")
hidRange = hid + Suppress("..") + hid
hidQ = Optional(Suppress(Keyword("hid:"))) + (hid^hidRange)
hidQ = hidQ.setParseAction(maybeRange("hid", dbname="id"))

# test event id
tid = Suppress("T")+Word("0123456789")
tidRange = tid + Suppress("..") + tid
tidQ = Optional(Suppress(Keyword("tid:"))) + (tid^tidRange)
tidQ = tidQ.setParseAction(maybeRange("tid", dbname="id"))

# External trigger event id
eid = Suppress("E")+Word("0123456789")
eidRange = eid + Suppress("..") + eid
eidQ = Optional(Suppress(Keyword("eid:"))) + (eid^eidRange)
eidQ = eidQ.setParseAction(maybeRange("eid", dbname="id"))

# Submitter
submitter = QuotedString('"').setParseAction(lambda toks: Q(submitter__name=toks[0]))
submitterQ = Optional(Suppress(Keyword("submitter:"))) + submitter
submitterQ = submitterQ.setParseAction(lambda toks: ("submitter", toks[0]))

# Created times

nltimeRange = nltime + Suppress("..") + nltime

def doTime(tok):
    x = datetime.datetime(*(map(int, tok)))
    return x

dash = Suppress('-')
colon = Suppress(':')
date_ = Regex(r'\d{4}') + dash +  Regex(r'\d{2}') + dash +  Regex(r'\d{2}')
dt = date_ + Optional(Regex(r'\d{2}')+colon+Regex(r'\d{2}')+
                Optional(colon+Regex(r'\d{2}')))
dt.setParseAction(doTime)

dtrange = dt + Suppress("..") + dt

createdQ = Optional(Suppress(Keyword("created:"))) + (nltime^nltimeRange^dt^dtrange)
createdQ = createdQ.setParseAction(maybeRange("created"))


# Labels
# XXX should we not get these from the DB?
labelNames = ["DQV", "INJ", "LUMIN_NO", "LUMIN_GO", "SWIFT_NO", "SWIFT_GO", "EM_READY", "cWB_r","cWB_s"]
label = Or([CaselessLiteral(n) for n in labelNames]).\
        setParseAction( lambda toks: Q(labels__name=toks[0]) )

andop   = oneOf(", &").suppress()
orop    = Literal("|").suppress()
minusop = oneOf("- ~").suppress()

labelQ_ = operatorPrecedence(label,
    [(minusop, 1, opAssoc.RIGHT, lambda a,b,toks: ~toks[0][0]),
     (orop,    2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__or__, toks[0].asList(), Q())),
     (andop,   2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__and__, toks[0].asList(), Q())),
    ]).setParseAction(lambda toks: toks[0])

labelQ = (Optional(Suppress(Keyword("label:"))) + labelQ_.copy())
labelQ.setParseAction(lambda toks: ("label", toks[0]))

###########################
# Query on event attributes

attrNumExprOperators = { "<" :  "__lt",
                         "<=":  "__lte",
                         "=" :  "",
                         ">" :  "__gt",
                         ">=":  "__gte",
                       }

attrNumExprLhs = Keyword("far") | Keyword("gpstime")

exponent = Combine(Word("Ee") + Optional(Word("+-"))+Word(nums))
afloat = Combine( Word(nums) + Optional(Combine(Literal(".") + Word(nums))) )

attrNumExprRhs = Combine( Optional(Word("+-")) + afloat + Optional(exponent) )
attrNumExprRhs.setParseAction(lambda toks: float(toks[0]))

attrNumExprOp = Or(map(Literal, attrNumExprOperators.keys()))
attrNumExprOp.setParseAction(lambda toks: attrNumExprOperators[toks[0]])

attrNumExpr = attrNumExprLhs + attrNumExprOp + attrNumExprRhs
attrNumExpr.setParseAction(lambda toks: Q(**{toks[0]+toks[1]: toks[2]}))

#attrIfoExpr = Keyword("ifos").suppress() + Literal("=").suppress() + Word("LVH12,")
#attrIfoExpr.setParseAction(lambda toks: Q(instruments=toks[0]))

#attrExpr = attrIfoExpr | attrNumExpr 
attrExpr = attrNumExpr 

attrExprs = operatorPrecedence(attrExpr,
    [(minusop, 1, opAssoc.RIGHT, lambda a,b,toks: ~toks[0][0]),
     (orop,    2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__or__, toks[0].asList(), Q())),
     (andop,   2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__and__, toks[0].asList(), Q())),
    ]).setParseAction(lambda toks: toks[0])


attributeQ = Optional(Suppress(Keyword('attr:'))) + attrExprs.copy()
attributeQ.setParseAction(lambda toks: ("attr", toks[0]))


###########################

ifoList = Regex(r'(L1|H1|H2|V1)(,(L1|H1|H2|V1))*')
ifoList.setParseAction(lambda toks: ("ifos", Q(instruments__contains=toks[0])))

ifoListQ = Optional(Suppress(Keyword("ifos:"))) + ifoList

nifoQ = Suppress(Keyword("nevents:")) + Word(nums)
nifoQ.setParseAction(lambda toks: ("nevents", Q(nevents=toks[0])))

ifoQ = ifoListQ | nifoQ

###########################

q = (ifoQ | hasfarQ | gidQ | hidQ | tidQ | eidQ | labelQ | atypeQ | groupQ | gpsQ | createdQ | submitterQ | runQ | attributeQ).setName("query term")

#andTheseTags = ["attr"]
andTheseTags = ["nevents"]

def parseQuery(s):
    d={}
    if not s:
        # Empty query return everything not in Test group
        return ~Q(group__name="Test")
    for (tag, qval) in (stringStart + OneOrMore(q) + stringEnd).parseString(s).asList():
        if tag in andTheseTags:
            d[tag] = d.get(tag,Q()) & qval
        else:
            d[tag] = d.get(tag,Q()) | qval
    if s.find("Test") < 0 and "tid" not in d:
        # If Test group is not mentioned in the query, we exclude it.
        if "group" in d:
            d["group"] &= ~Q(group__name="Test")
        else:
            d["group"] = ~Q(group__name="Test")
    if "tid" in d:
        d["tid"] = d["tid"] & Q(group__name="Test")
    if "hid" in d:
        d["hid"] = d["hid"] & Q(analysisType="HWINJ")
    if "eid" in d:
        d["eid"] = d["eid"] & Q(analysisType="GRB")
    if "id" in d:
        d["id"] = d["id"] & ~Q(analysisType="HWINJ") & ~Q(analysisType="GRB")
    if "id" in d and "hid" in d:
        d["id"] = d["id"] | d["hid"]
        del d["hid"]
    return reduce(Q.__and__, d.values(), Q())

