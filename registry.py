_registry = {}


def instance(cls):
    _registry[cls.__name__.lower()] = cls()
    return cls


def inject_all():
    for key in _registry:
        _registry[key].inject(get_instance)


def get_instance(name):
    if name.lower() in _registry:
        return _registry[name.lower()]
    else:
        return None
