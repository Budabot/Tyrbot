from core.registry import Registry


# taken from: https://stackoverflow.com/a/26151604/280574
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


@parametrized
def command(handler, command, params, access_level, description, sub_command=None, help_file=None):
    handler.command = [command, params, access_level, description, help_file, sub_command]
    return handler


@parametrized
def event(handler, event_type, description):
    handler.event = [event_type, description]
    return handler


@parametrized
def timerevent(handler, budatime, description):
    util = Registry.get_instance("util")
    t = util.parse_time(budatime)
    handler.event = ["timer:" + str(t), description]
    return handler
