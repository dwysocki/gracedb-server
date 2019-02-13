from __future__ import absolute_import
from pyparsing import oneOf, Literal, Optional, ZeroOrMore, StringEnd, Suppress

from django.db.models import Q

from events.models import Label


OPERATORS = {
    'AND': oneOf(", &"),
    'OR': Literal("|"),
    'NOT': oneOf("- ~"),
}


def parse_label_query(s):
    """Parses a label query into a list of label names"""
    # Parser for one label name
    label = oneOf(list(Label.objects.all().values_list('name', flat=True)))

    # "intermediate" parser - between labels should be AND or OR and then
    # an optional NOT
    im = Suppress((OPERATORS['AND'] ^ OPERATORS['OR']) +
        Optional(OPERATORS['NOT']))

    # Full parser: optional NOT and a label, then zero or more
    # "intermediate" + label combos, then string end
    labelQ = Suppress(Optional(OPERATORS['NOT'])) + label + \
        ZeroOrMore(im + label) + StringEnd()
    
    return labelQ.parseString(s).asList()
