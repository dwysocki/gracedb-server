import string

# Get lowercase alphabet as string
ALPHABET = string.ascii_lowercase
BASE = len(ALPHABET)

def int_to_letters(num, positive_only=True):
    """

    Enumeration starts at 1 (i.e., 1 => 'a')
    """

    # Argument checking
    if not isinstance(num, int):
        raise TypeError("Input 'num' is not an int")
    if (positive_only and num <= 0):
        raise ValueError(("Input 'num' is non-positive, but the positive_only "
            "flag is set"))

    out_str = ''
    while (num > BASE):
        r = num % BASE
        num /= BASE
        out_str = ALPHABET[r-1] + out_str
    out_str = ALPHABET[num-1] + out_str
    return out_str

def letters_to_int(letters):
    # TODO: remove assert statement!
    assert isinstance(letters, str), "letters is not a string"

    letters = letters.lower()
    pass
