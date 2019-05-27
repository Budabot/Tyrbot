import itertools


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


# taken from: https://stackoverflow.com/a/8529229/280574 and modified
def get_attrs(obj):
    attrs = {}
    for cls in obj.__class__.__mro__:
        attrs.update(cls.__dict__.items())
    attrs.update(obj.__class__.__dict__.items())
    return attrs
