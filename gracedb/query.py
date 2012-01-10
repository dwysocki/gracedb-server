
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


q = (hasfarQ | gidQ | hidQ | tidQ | labelQ | atypeQ | groupQ | gpsQ | createdQ | submitterQ).setName("query term")

def parseQuery(s):
    d={}
    for (tag, qval) in (stringStart + OneOrMore(q) + stringEnd).parseString(s).asList():
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
    if "id" in d:
        d["id"] = d["id"] & ~Q(analysisType="HWINJ")
    if "id" in d and "hid" in d:
        d["id"] = d["id"] | d["hid"]
        del d["hid"]
    return reduce(Q.__and__, d.values(), Q())

