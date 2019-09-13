try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest
from rest_framework.exceptions import ValidationError

from ..fields import EventGraceidField


@pytest.mark.parametrize(
    "graceid",
    [1234, 1.234, (), [], None, True, lambda x: x]
)
def test_bad_types(graceid):
    field = EventGraceidField()

    err_msg = 'Event graceid must be a string.'
    with pytest.raises(ValidationError, match=err_msg):
        field.to_internal_value(graceid)


@pytest.mark.parametrize(
    "graceid",
    ['GG', '1234G', 'G.1234', 'G1234z', 'Q1234', 'GH12']
)
def test_graceid_bad_format(graceid):
    field = EventGraceidField()

    err_msg = 'Not a valid graceid.'
    with pytest.raises(ValidationError, match=err_msg):
        field.to_internal_value(graceid)


@pytest.mark.parametrize(
    "graceid",
    ['G1234', 'E0001', 'H12', 'M352345', 'T2323', ' T123', 'T123 ', ' T123 ',
     'g4567', 't456 ', ' m2398     ', '  e8732']
)
def test_valid_graceids(graceid):
    field = EventGraceidField()

    # WHY do we have to mock this as 'gracedb.api...'
    # instead of just 'api...'??
    super_tiv = 'gracedb.api.v1.fields.GenericField.to_internal_value'
    with mock.patch(super_tiv) as mock_super_tiv:
        field.to_internal_value(graceid)

    call_args, _ = mock_super_tiv.call_args
    assert mock_super_tiv.call_count == 1
    assert len(call_args) == 1
    assert call_args[0] == graceid.upper().strip()
