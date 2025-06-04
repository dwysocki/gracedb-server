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

# FAR Unit conversions (fixed 2024/3/1, big error in hr_to_yr)
# Note that the converstion error that was just fixed was only
# in the web page display, so there's thankfully no values in the
# database to go back and fix.

far_hr_to_yr = 24*settings.DAYS_PER_YEAR 		# 1/yr = 1/hr * (8760ish hr/year)
far_sec_to_year = 60*60*24*settings.DAYS_PER_YEAR	# 1 yr = (sec/min) * (min/hr) * (hr/day) * (day/year) sec
far_yr_to_sec = 1.0/far_sec_to_year			# ^^ inverse of that
far_hr_to_sec = far_hr_to_yr * far_yr_to_sec   		# 1/sec =  1/hr * (8760 hr/ yr) * (1 yr/ 3.154e7 sec)

# Unit formats:
per_hr_formats = ['1/hr', 'hr^-1', '1/hour', 'hour^-1']
per_yr_formats = ['1/yr', 'yr^-1', '1/year', 'year^-1']


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


def display_far_hz_to_yr(display_far):
    """
    A helper function to change hz far value to a nicely formatted
    /year value for use in tables and such.
    """

    # Determine "human-readable" FAR to display
    display_far_hr = display_far
    if display_far:
        # FAR in units of yr^-1
        far_yr = display_far * far_sec_to_year
        if (far_yr < 1):
            display_far_hr = "1 per {0:0.5g} years".format(1.0/far_yr)
        else:
            display_far_hr = "{0:0.5g} per year".format(far_yr)

    return display_far_hr


def return_far_in_hz(far_in, units=None):
    """
    A helper function that takes in a far value and a set of units
    and returns the value in Hz. expects /hr or /yr atm.

    Raising errors instead of 400's is probably safe here, since users
    never directly call this function from the API.
    """

    # Check if units were provided, if not, quit
    if not units: raise ValueError('no units input')

    # Make sure the units are a string:
    if not isinstance(units, str): raise TypeError('units must be a string')

    # Change the units' formatting so they match the templates:
    # make it lowercase and get rid of any spaces:
    units_in = units.lower().replace(' ', '')

    # Convert per hour:
    if units_in in per_hr_formats:
        return far_in * far_hr_to_sec

    # Convert per year:
    elif units_in in per_yr_formats:
        return far_in * far_yr_to_sec

    # Log and give up if not recognized:
    else:
        logger.debug('could not recognize input far units')
        return None


def return_safe_value(val, string=""):
    return val if val is not None else string


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
