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
    "O4": {
            # https://wiki.ligo.org/Operations/Agenda250109
            # O4b -> O4c transition will happen on Tuesday Jan. 28th at 1700 UTC
            # (GPS: 1422118818).
            # EDIT: O4c extended to Oct 7 2025 1500UTC:
            # https://observing.docs.ligo.org/plan/
            "O4c": (1422118818, 1443884418),
            # https://observing.docs.ligo.org/plan/
            # The LIGO Hanford (LHO), LIGO Livingston (LLO), and Virgo detectors transitioned
            # to the regular observing run O4b at 15:00 UTC on 10 April 2024. O4b will run
            # until 9 June 2025 (assuming 15:00 UTC but FIXME later).
            "O4b": (1396796418, 1422118818),
            # O4a started May 24, 2023 1500UTC and ended Jan 16, 2024 1600UTC
            "O4a": (1368975618, 1389456018),
          },
    # ER16 started March 20, 2024 1500UTC, ended when O4b started
    # https://dcc.ligo.org/DocDB/0191/M2300233/002/ER16_O4b_Start.pdf
    "ER16": (1394982018, 1396796418),
    # ER15 start Apr 26, 2023 1500 UTC
    "ER15": (1366556418, 1368975618),
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

# Flattens run map, creating a consistently typed dict mapping
# run/segment names to a list of (start, stop) gpstimes.
def flatten_run_map(dictionary):
    flattened = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            # Insert the full run
            flattened[key] = list(value.values())
            # Insert the individual segments
            for segment_name, segment_times in value.items():
                flattened[segment_name] = [segment_times]
        else:
            # Insert a full run that has no segments
            flattened[key] = [value]

    return flattened

# A flat RUN_MAP list to use in queries:
RUN_MAP_FLAT = flatten_run_map(RUN_MAP)
