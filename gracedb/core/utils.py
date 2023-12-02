import logging
from pathlib import Path
import re
import string

from django.conf import settings
from django.views.debug import ExceptionReporter

from six import string_types

# Set up logger
logger = logging.getLogger(__name__)

# Get lowercase alphabet as string
ALPHABET = string.ascii_lowercase
BASE = len(ALPHABET)
ASCII_ALPHABET_START = ord('a') - 1

# Unit conversions
far_hr_to_yr = 86400*365.25


def int_to_letters(num, positive_only=True):
    """
    Convert a base 10 int to a base 26 representation using the English
    alphabet.  Enumeration starts at 1 (i.e., 1 => 'a')
    """

    # Argument checking
    if not isinstance(num, int):
        # Coerce to int
        logger.warning('Coercing argument of type {0} to int'.format(
            type(num)))
        num = int(num)
    if (positive_only and num <= 0):
        raise ValueError(("Input 'num' is non-positive, but the positive_only "
            "flag is set"))

    out_str = ''
    while num:
        num, remainder = divmod(num - 1, BASE)
        out_str = chr(ASCII_ALPHABET_START + 1 + remainder) + out_str
    return out_str


def letters_to_int(letters):
    """
    Converts string of English letters from base 26 to a base 10 int.
    Uppercase letters are converted to lowercase.
    """

    # Require string-type input
    if not isinstance(letters, string_types):
        raise TypeError('input should be a string')

    # Convert to lowercase
    letters = letters.lower()

    # Make sure all characters are in ALPHABET
    if not set(letters).issubset(ALPHABET):
        raise ValueError('input should be in a-z')

    # Do the actual conversion
    num = sum([(BASE**i)*(ord(l)-ASCII_ALPHABET_START) for i,l in
        enumerate(letters[::-1])])

    return num


def display_far_hr_to_yr(display_far):
    """
    A helper function to change /hr far value to a nicely formatted
    /year value for use in tables and such.
    """

    # Determine "human-readable" FAR to display
    display_far_hr = display_far
    if display_far:
        # FAR in units of yr^-1
        far_yr = display_far * far_hr_to_yr
        if (far_yr < 1):
            display_far_hr = "1 per {0:0.5g} years".format(1.0/far_yr)
        else:
            display_far_hr = "{0:0.5g} per year".format(far_yr)

    return display_far_hr


class CustomExceptionReporter(ExceptionReporter):
    """
    Custom Django exception reporter, used in DEBUG mode.  Overrides default
    templates with ones that do not expose our settings.
    """

    @property
    def html_template_path(self):
        return Path(settings.PROJECT_ROOT) / 'templates' / 'technical_500.html'

    @property
    def text_template_path(self):
        return Path(settings.PROJECT_ROOT) / 'templates' / 'technical_500.txt'
