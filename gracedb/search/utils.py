import logging
from pyparsing import Keyword, CaselessKeyword, oneOf, Literal, Or, \
    OneOrMore, ZeroOrMore, Optional, Suppress

from django.db.models import Q, QuerySet

# Set up logger
logger = logging.getLogger(__name__)


def maybeRange(name, dbname=None):
    """
    Creates a parser action which takes one or two tokens.  If there are two
    tokens, the action is to query the range between them.  If there is one
    token, the action is to query that value alone.

    Query takes place over ``dbname`` if set, otherwise ``name``

    Query will be tagged according to ``name``.
    """
    dbname = dbname or name
    def f(toks):
        if len(toks) == 1:
            return name, Q(**{dbname: toks[0]})
        return name, Q(**{dbname+"__range": toks.asList()})
    return f

# Given a list of the tokens, go through the list until you hit an AND or
# OR operator. Then apply the operator to the two surrounding query sets
# and send back a new list. The list will be shorter by 2 elements, since
# 'QuerySet, op, QuerySet' has been replaced by a single QuerySet.
#--------------------------------------------------------------------------
def handle_binary_ops(toks, op="or"):

    # Find the indices of the relevant operators.
    if op == "or":
        indices = [i for i, x in enumerate(toks) if x is '|']
    elif op == "and":
        indices = [i for i, x in enumerate(toks) if x == '&' or x==',']
    else:
        raise ValueError("Unknown operator")

    if len(indices) > 0:
        # Found the operator we're looking for
        updated = True
        i = indices[0]  # index of the first operator in the list
        leftQS = toks[i-1]
        rightQS = toks[i+1]

        # Check. The list items surrounding our operator need to be QuerySets
        if (not isinstance(leftQS, QuerySet)
            or not isinstance(rightQS, QuerySet)):
            raise ValueError("problem with query. Orphaned operator?")

        # Combine the two QuerySets
        if op=="or":
            outputQ = leftQS | rightQS
        elif op=="and":
            outputQ = leftQS & rightQS

        # Build up the new list of tokens to return.
        new_toks = []
        for j in range(len(toks)):
            if j == i-1:
                new_toks.append(outputQ)
            elif j==i or j==i+1:
                continue
            else:
                new_toks.append(toks[j])

    else:
        # No such operator found, return the list of tokens unmodified.
        updated = False
        new_toks = toks

    return new_toks, updated
