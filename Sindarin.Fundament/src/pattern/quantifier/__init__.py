

#
# These were suggested in PEP 316
#

def forall(a, fn = bool):
    """Return True only if all elements in a are true.

    >>> forall([])
    1
    >>> even = lambda x: x % 2 == 0
    >>> forall([2, 4, 6, 8], even)
    1
    >>> forall('this is a test'.split(), lambda x: len(x) == 4)
    0
    """
    for x in a:
        if not fn(x): return False
    else:
        return True

def exists(a, fn = bool):
    """Returns True if there is at least one true value in a.

    >>> exists([])
    0
    >>> exists('this is a test'.split(), lambda x: len(x) == 4)
    1
    """
    for x in a:
        if fn(x): return True
    else:
        return False
