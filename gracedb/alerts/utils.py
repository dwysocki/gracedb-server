from __future__ import absolute_import
from pyparsing import (
    oneOf, Optional, ZeroOrMore, StringEnd, Suppress, infixNotation, opAssoc,
)
import re

from events.models import Label
from .constants import OPERATORS


def get_label_parser():
    return oneOf(list(Label.objects.values_list('name', flat=True)))


def parse_label_query(s, keep_binary_ops=False):
    """
    Parses a label query into a list. The output is a list whose elements
    depend on the options:

    >>> parse_label_query('A & B', keep_binary_ops=False)
        ['A', 'B']
    >>> parse_label_query('A & B', keep_binary_ops=True)
        ['A', '&', 'B']
    """
    # Parser for one label name
    label = get_label_parser()

    # "intermediate" parser - between labels should be AND or OR and then
    # an optional NOT
    im = (OPERATORS['AND'] ^ OPERATORS['OR']) + Optional(OPERATORS['NOT'])
    if not keep_binary_ops:
        im = Suppress(im)

    # Full parser: optional NOT and a label, then zero or more
    # "intermediate" + label combos, then string end
    optional_initial_not = Optional(OPERATORS['NOT'])
    if not keep_binary_ops:
        optional_initial_not = Suppress(optional_initial_not)
    label_expr = optional_initial_not + label + \
        ZeroOrMore(im + label) + StringEnd()

    return label_expr.parseString(s).asList()


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


def get_label_query_parser(label_name_list):
    label_parser = get_label_parser()
    label_parser.setParseAction(lambda toks: toks[0] in label_name_list)
    label_query_parser = infixNotation(label_parser,
        [
            (OPERATORS['NOT'], 1, opAssoc.RIGHT, lambda toks: not toks[0][1]),
            (OPERATORS['AND'], 2, opAssoc.LEFT, lambda toks: all(toks[0][0::2])),
            (OPERATORS['OR'], 2, opAssoc.LEFT, lambda toks: any(toks[0][0::2])),
        ]
    )
    return label_query_parser


def evaluate_label_queries(label_name_list, notifications):
    """
    Takes in a list of label names and a queryset of Notifications,
    returns pks of Notifications which have a label_query and that
    label_query is evaluates to True
    """
    label_query_parser = get_label_query_parser(label_name_list)

    notification_pks = []
    for n in notifications.filter(label_query__isnull=False):
        valid = label_query_parser.parseString(n.label_query)[0]
        if valid:
            notification_pks.append(n.pk)

    return notification_pks
