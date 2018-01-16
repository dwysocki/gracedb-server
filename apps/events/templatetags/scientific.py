
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django import template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils import formats
register = template.Library()

# Florian Lauck, 2010
# If you find this code useful please leave a comment on my blog:
# http://classmplanet.wordpress.com/

# see /django/template/defaultfilters.py
pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) / (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]

@register.filter("scientific")
def scientific(text):
    if text is None:
        return mark_safe("")
    try:
        out = "%0.3e" % text
    except:
        return text
    return mark_safe(out)

@register.filter("scientificformat")
def scientificformat(text):
    """
    Displays a float in scientific notation.

    If the input float is infinity or NaN, the (platform-dependent) string
    representation of that value will be displayed.

    This is based on the floatformat function in django/template/defaultfilters.py
    """

    try:
        input_val = force_unicode(text)
        d = Decimal(input_val)
    except UnicodeEncodeError:
        return u''
    except InvalidOperation:
        if input_val in special_floats:
            return input_val
        try:
            d = Decimal(force_unicode(float(text)))
        except (ValueError, InvalidOperation, TypeError, UnicodeEncodeError):
            return u''

    try:
        m = int(d) - d
    except (ValueError, OverflowError, InvalidOperation):
        return input_val

    try:
        # for 'normal' sized numbers
        if d.is_zero():
            number = u'0'
        elif ( (d > Decimal('-100') and d < Decimal('-0.1')) or ( d > Decimal('0.1') and d < Decimal('100')) ) :
            # this is what the original floatformat() function does
            sign, digits, exponent = d.quantize(Decimal('.01'), ROUND_HALF_UP).as_tuple()
            digits = [unicode(digit) for digit in reversed(digits)]
            while len(digits) <= abs(exponent):
                digits.append(u'0')
            digits.insert(-exponent, u'.')
            if sign:
                digits.append(u'-')
            number = u''.join(reversed(digits))
        else: 
            # for very small and very large numbers
            sign, digits, exponent = d.as_tuple()
            exponent = d.adjusted()
            digits = [unicode(digit) for digit in digits][:3] # limit to 2 decimal places
            while len(digits) < 3:
                digits.append(u'0')
            digits.insert(1, u'.')
            if sign:
                digits.insert(0, u'-')
            number = u''.join(digits)
            number += u'e' + u'%i' % exponent

        return mark_safe(formats.number_format(number))
    except InvalidOperation:
        return input_val
scientificformat.is_safe = True
