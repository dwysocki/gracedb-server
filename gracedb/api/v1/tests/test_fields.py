from __future__ import absolute_import
import decimal
import math

from django.test import SimpleTestCase

from ..fields import CustomDecimalField


class TestCustomDecimalField(SimpleTestCase):
    """
    Test different conversions of floats to decimal.Decimals using
    CustomDecimalField. This class is only different from the default
    DecimalField provided by rest_framework for floats, so we don't need to
    test other data types.
    """

    def test_lots_of_floats(self):
        # Setup
        DECIMAL_PLACES = 6
        raw_int = 1234567890

        MAX_DIGITS = int(math.ceil(math.log10(raw_int))) + DECIMAL_PLACES
        df = CustomDecimalField(MAX_DIGITS, DECIMAL_PLACES)
        for exp in range(0, DECIMAL_PLACES):
            for num in range(0, 10):
                decimal_places_as_int = num * (10**exp)
                raw_float = raw_int + decimal_places_as_int * \
                    (10**(-1*DECIMAL_PLACES))
                raw_str = str(raw_int) + '.' + '{{:0>{dp}}}'.format(
                    dp=DECIMAL_PLACES).format(decimal_places_as_int)
                output = df.to_internal_value(raw_float)
                self.assertEqual(output.to_eng_string(), raw_str)

