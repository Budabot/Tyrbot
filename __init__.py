import itertools


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


def none_to_empty_string(val):
    if val:
        return val
    else:
        return ""
