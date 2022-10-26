try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import string

import pytest
import itertools

from alerts.constants import AND, OR, NOT
from alerts.utils import get_label_query_parser, parse_label_query
from events.models import Label

# NOTE: list('ABC') == ['A', 'B', 'C']
@pytest.mark.parametrize(
    "labels,label_query,match",
    [
        (['A'], 'A & B', False),
        (['A', 'B'], 'A & B', True),
        (['A', 'B'], '~B', False),
        (['A', 'B'], '~B', False),
        (['A', 'B'], '~B', False),
        (list('ABC'), 'A & B', True),
        (['C'], 'A & B | C', True),
        (['C'], '~C | B', False),
        (list('ABCD'), 'A & B & C & D', True),
        (list('ABCD'), 'A & B & C & D & ~E', True),
        (list('ABCD'), 'A & B & C & D & E', False),
        (list('ABCD'), 'A & C | C & ~E', True),
        (list('ABCD'), '~A | C & ~E', True),
        (list('ABCD'), '~A | D & E', False),
        (list('ABCD'), 'A', True),
        (list('ABCD'), 'A | F | G | H', True),
        (list('ABCD'), 'E | F | C | H', True),
        (list('ABCD'), 'Y | F | Z | H', False),
        (list('ABCD'), 'A & B | ~C & ~D', True),
        # Try a few with werid spacings
        (list('ABCD'), 'A|D &~E', True),
        (['A', 'B'], '~A |B&C&~D', False),
        (['A', 'B'], 'A| B|C&~D', True),
    ]
)
def test_label_query_parsing(labels, label_query, match):
    label_list_method = 'alerts.utils.Label.objects.values_list'
    #with mock.patch('alerts.utils.get_label_parser') as mock_glp:
    with mock.patch(label_list_method) as mock_llm:
        mock_llm.return_value = list(string.ascii_uppercase)
        lqp = get_label_query_parser(labels)
    assert lqp.parseString(label_query)[0] == match


PARSE_LABEL_QUERY_INPUTS_OUTPUTS = [
    ('{A} & {B}', False, ['{A}', '{B}']),
    ('{A} & {B}', True, ['{A}', '&', '{B}']),
]
@pytest.mark.parametrize(
    "query,keep_binary_ops,output",
    PARSE_LABEL_QUERY_INPUTS_OUTPUTS,
)
@pytest.mark.django_db
def test_parse_label_query(query, keep_binary_ops, output):
    labels = Label.objects.values_list('name', flat=True)
    for A_label, B_label in itertools.product(labels, repeat=2):
        query_labeled = query.format(A=A_label, B=B_label)
        output_labeled = [elem.format(A=A_label, B=B_label) for elem in output]
        test_output_labeled = parse_label_query(query_labeled,
                                                keep_binary_ops=keep_binary_ops)
        assert output_labeled == test_output_labeled


@pytest.mark.parametrize("num_labels", range(1, 5))
@pytest.mark.django_db
def test_parse_label_query(num_labels):
    """Test many possible inputs to `parse_label_query`"""
    # Test with/without whitespace separators.
    separator_choices = ['', ' ', '\t']

    # Replace DB's Label set with `num_labels` unique values, as the
    # allowed labels shouldn't matter.
    labels = replace_label_set(num_labels)

    # Test all possible combinations of binary and unary operators.
    binary_operator_choices = itertools.product(AND+OR, repeat=num_labels-1)
    unary_operator_choices = itertools.product(NOT + [''], repeat=num_labels)
    operator_choices = itertools.product(binary_operator_choices,
                                         unary_operator_choices)
    for binary_operators, unary_operators in operator_choices:
        # Expected output if operators are kept
        # NOTE: this is also how we construct the query
        expected_output_keep_ops = [
            token
            for token in roundrobin(unary_operators, labels, binary_operators)
            if token != '' # filter out empty unary operators
        ]

        # Expected output if operators are not kept
        expected_output_no_keep_ops = labels
        # # NOTE: This is what would be expected if `keep_binary_ops` only acted
        # #       on the _binary_ operators, and left the unary operators alone.
        # expected_output_no_keep_ops = [
        #     token
        #     for token in roundrobin(unary_operators, labels)
        #     if token != '' # filter out empty unary operators
        # ]

        # Test all allowed separators
        for separator in separator_choices:
            # Construct the query from tokens
            query = separator.join(expected_output_keep_ops)

            # Get the actual output with/without operators kept
            actual_output_no_keep_ops = parse_label_query(query,
                                                          keep_binary_ops=False)
            actual_output_keep_ops = parse_label_query(query,
                                                       keep_binary_ops=True)

            # Assert that the output is what's expected
            assert expected_output_no_keep_ops == actual_output_no_keep_ops
            assert expected_output_keep_ops == actual_output_keep_ops


def replace_label_set(num_labels):
    # Delete existing labels
    Label.objects.all().delete()

    # Create a new set of labels
    names = []
    for i in range(num_labels):
        name = f'label{i}'
        description = f'Fake label number {i}'
        Label.objects.create(name=name, description=description)
        names.append(name)

    # Return the new labels' names
    return names


def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    num_active = len(iterables)
    nexts = itertools.cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = itertools.cycle(itertools.islice(nexts, num_active))
