import itertools


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))