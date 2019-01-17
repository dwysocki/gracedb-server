from __future__ import absolute_import
import logging
from pyparsing import Keyword, CaselessKeyword, oneOf, Literal, Or, \
    OneOrMore, ZeroOrMore, Optional, Suppress

from django.db.models import Q

from events.models import Label
from ..utils import handle_binary_ops

# Set up logger
logger = logging.getLogger(__name__)


def getLabelQ():
    # labelQ is defined inside in order to avoid a compile-time database query
    # to get the label names.
    # Note the parse action for labelQ: Replace all tokens with the empty
    # string. This basically has the effect of removing any label query terms
    # from the query string.
    labelNames = [l.name for l in Label.objects.all()]
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

    return labelQ


#--------------------------------------------------------------------------
# Given a query string, separate out the label-related part, and return it
# as a list of Q objects and separators.
#--------------------------------------------------------------------------
def labelQuery(s, names=False):
    labelNames = [l.name for l in Label.objects.all()]
    #label = Or([CaselessLiteral(n) for n in labelNames])
    label = Or([CaselessKeyword(n) for n in labelNames])
    # If the filter objects are going to be applied to Lable
    # objects to retrieve labels by name, names = True.
    # This is useful for the label query in alerts.models.Notification
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
    labelNames = [l.name for l in Label.objects.all()]
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
