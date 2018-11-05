from pyparsing import Literal, Or

# Create a parser for translating comparison operators to
# Django queryset filter keywords
EXPR_OPERATORS = {
    "<" :  "__lt",
    "<=":  "__lte",
    "=" :  "",
    "==" :  "",
    ":" :  "",
    ">" :  "__gt",
    ">=":  "__gte",
}
ExpressionOperator = Or(map(Literal, EXPR_OPERATORS.keys()))
ExpressionOperator.setParseAction(lambda toks: EXPR_OPERATORS[toks[0]])


# Dict of LIGO run names (keys) and GPS time range tuples (values)
RUN_MAP = {
    # 30 Nov 2016 16:00:00 UTC - 25 Aug 2017 22:00:00 UTC
    "O2"  :     (1164556817, 1187733618),
    # Friday, Sept 18th, 10 AM CDT 2015 - Tuesday, Jan 12th, 10:00 AM CST 2016
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

