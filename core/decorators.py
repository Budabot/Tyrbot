from core.registry import Registry


# taken from: https://stackoverflow.com/a/26151604/280574
def parameterized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


@parameterized
def instance(cls, name=None, override=False):
    instance_name = name if name else cls.__name__
    Registry.add_instance(instance_name, cls(), override)
    return cls


@parameterized
def command(handler, command, params, access_level, description, sub_command=None, help_file=None, extended_description=None):
    handler.command = [command, params, access_level, description, help_file, sub_command, extended_description]
    return handler


@parameterized
def event(handler, event_type, description, is_hidden=False, is_enabled=True):
    handler.event = [event_type, description, is_hidden, is_enabled]
    return handler


@parameterized
def timerevent(handler, budatime, description, is_hidden=False, is_enabled=True):
    util = Registry.get_instance("util")
    t = util.parse_time(budatime)
    handler.event = ["timer:" + str(t), description, is_hidden, is_enabled]
    return handler


@parameterized
def setting(handler, name, value, description, extended_description=None):
    obj = handler(None)

    def new_handler(self):
        return obj

    new_handler.setting = [name, value, description, extended_description, obj]
    new_handler.__module__ = handler.__module__
    return new_handler
