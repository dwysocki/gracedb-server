from __future__ import absolute_import
from pyparsing import oneOf, Literal, Optional, ZeroOrMore, StringEnd, Suppress
import re

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


def convert_superevent_id_to_speech(sid):
    """Used for Twilio voice calls"""
    grps = list(re.match('^(\w+)(\d{2})(\d{2})(\d{2})(\w+)$', sid).groups())

    # Add spaces between all letters in prefix and suffix
    grps[0] = " ".join(grps[0])
    grps[-1] = " ".join(grps[-1])

    # Join with spaces, replace leading zeroes with Os
    # and make uppercase
    twilio_str = " ".join(grps).replace(' 0', ' O').upper()
    return twilio_str
