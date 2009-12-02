
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

from models import Event
from django.db.models import Q

from pyparsing import \
    Word, nums, Literal, delimitedList, Suppress, Group, \
    Keyword, Combine, Or, Optional, OneOrMore, alphas, Regex, \
    opAssoc, operatorPrecedence, oneOf, \
    stringStart, stringEnd, ParseException

def maybeRange(name):
    def f(toks):
        if len(toks) == 1:
            return name, Q(**{name: toks[0]})
        return name, Q(**{name+"__range": toks.asList()})
    return f

encodeType = dict([(x[1],x[0]) for x in Event.ANALYSIS_TYPE_CHOICES])

def doType(toks):
    return ("type", Q(analysisType__in=[encodeType[tok] for tok in toks]))

def convertToGps(dateStr):
    return 12

def doDate(toks):
    if len(toks) == 1:
        return "gpstime", Q("gpstime", convertToGps(toks[0]))
    return "gpstime", Q("gpstime__range", map(convertToGps(toks.toList())))

# GPS Times
gpstime = Word(nums).setName("GPS time")
gpstimeRange = (gpstime + Suppress("..") + gpstime).setName("GPS time range")

gpsQ = Optional(Suppress(Keyword("gpstime:"))) + (gpstime^gpstimeRange)
gpsQ = gpsQ.setParseAction(maybeRange("gpstime"))

# Analysis Groups
groupNames = ["Test", "Burst", "CBC", "Stochastic", "CW"]
group = Or(map(Literal, groupNames)).setName("analysis group name")
groupList = delimitedList(group, delim='|').setName("analysis group list")
groupQ = (Optional(Suppress(Keyword("group:"))) + groupList)
groupQ = groupQ.setParseAction(lambda toks: ("group", Q(group__name__in=toks.asList())))


# Analysis Types
atypeNames = ["LowMass", "HighMass", "Inspiral", "Omega", "X"]
atypeNames = encodeType.keys()
atype = Or(map(Literal, atypeNames))
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

# Labels
labelNames = ["DQV", "INJ", "LUMIN_NO", "LUMIN_GO", "SWIFT_NO", "SWIFT_GO"]
label = Or([Literal(n) for n in labelNames]).\
        setParseAction( lambda toks: Q(labels__name=toks[0]) )

andop   = oneOf(", &").suppress()
orop    = Literal("|").suppress()
minusop = oneOf("- ~").suppress()

labelQ_ = operatorPrecedence(label,
    [(minusop, 1, opAssoc.RIGHT, lambda a,b,toks: ~toks[0][0]),
     (orop,    2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__or__, toks[0].asList(), Q())),
     (andop,   2, opAssoc.LEFT,  lambda a,b,toks: reduce(Q.__and__, toks[0].asList(), Q())),
    ]).setParseAction(lambda toks: toks[0])

labelQ = labelQ_.copy().setParseAction(lambda toks: ("label", toks[0]))

# Date/Time
# XXX Not yet included... requires conversion to gps.
dateTime = Regex(r'\d{4}/\d{2}/\d{2}(-\d{2}:\d{2}(:\d{2})?( ?[A-Z]{3,4})?)?')
dateQ = (Optional(Suppress(Keyword("date:"))) + dateTime).\
        setParseAction(doDate)


q = (gidQ | groupQ | atypeQ | gpsQ | labelQ ).setName("query term")

def parseQuery(s):
    d={}
    for (tag, qval) in (stringStart + OneOrMore(q) + stringEnd).parseString(s).asList():
        d[tag] = d.get(tag,Q()) | qval
    if s.find("Test") < 0:
        # Test group is not mentioned in the query, so we exclude it.
        if "group" in d:
            d["group"] &= ~Q(group__name="Test")
        else:
            d["group"] = ~Q(group__name="Test")
    return reduce(Q.__and__, d.values(), Q())

