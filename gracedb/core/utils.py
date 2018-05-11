from django.utils.six import string_types

import string

import logging
logger = logging.getLogger(__name__)

# Get lowercase alphabet as string
ALPHABET = string.ascii_lowercase
BASE = len(ALPHABET)
ASCII_ALPHABET_START = ord('a') - 1

def int_to_letters(num, positive_only=True):
    """
    Enumeration starts at 1 (i.e., 1 => 'a')
    """

    # Argument checking
    if not isinstance(num, (int, long)):
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
    # TODO: remove assert statement!
    assert isinstance(letters, string_types), "letters is not a string"

    # Convert to lowercase
    letters = letters.lower()

    num = sum([(BASE**i)*(ord(l)-ASCII_ALPHABET_START) for i,l in
        enumerate(letters[::-1])])

    return num
