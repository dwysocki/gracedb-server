try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import string

import pytest

from alerts.utils import get_label_query_parser

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
