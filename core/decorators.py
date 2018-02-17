from core.registry import Registry


def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


@parametrized
def instance(cls, name=None):
    instance_name = cls.__name__ if name is None else name
    Registry.add_instance(instance_name, cls())
    return cls
