from pyparsing import oneOf, Literal


# List of characters which are equivalent to the corresponding
# logical operator
AND = ['&', ',']
OR = ['|']
NOT = ['~', '-']


# Pyparsing parsers
OPERATORS = {
    'NOT': oneOf(NOT),
    'AND': oneOf(AND),
    'OR': Literal(OR),
}
