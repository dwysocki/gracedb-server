import logging
import string

from six import string_types

# Set up logger
logger = logging.getLogger(__name__)

# Get lowercase alphabet as string
ALPHABET = string.ascii_lowercase
BASE = len(ALPHABET)
ASCII_ALPHABET_START = ord('a') - 1


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
