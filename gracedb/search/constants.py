from pyparsing import Literal, Or

# Create a parser for translating comparison operators to
# Django queryset filter keywords
EXPR_OPERATORS = {
    "<": "__lt",
    "<=": "__lte",
    "=": "",
    "==": "",
    ":": "",
    ">": "__gt",
    ">=": "__gte",
}
ExpressionOperator = Or(list(map(Literal, list(EXPR_OPERATORS))))
ExpressionOperator.setParseAction(lambda toks: EXPR_OPERATORS[toks[0]])


# Dict of LIGO run names (keys) and GPS time range tuples (values)
RUN_MAP = {
    # O4 Start May 24, 2023...1500UTC? 18 months later...Nov. 24, 2024.
    # FIXME: change the end date in a future release:
    "O4": (1368975618, 1416495618),
    # O3 suspended early due to COVID-19:
    # https://www.ligo.caltech.edu/news/ligo20200326
    # 01 Apr 2019 15:00:00 UTC - 27 Mar 2020 16:00:00 UTC
    "O3": (1238166018, 1269363618),
    # 04 Mar 2019 16:00:00 UTC - 01 Apr 2019 15:00:00 UTC
    "ER14": (1235750418, 1238166018),
    # 14 Dec 2018 16:00:00 UTC - 18 Dec 2018 14:00:00 UTC
    "ER13": (1228838418, 1229176818),
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

