import re
from core.registry import Registry
from core.map_object import MapObject


class CommandParam:
    def __init__(self):
        pass

    def get_regex(self):
        pass

    def get_name(self):
        pass


class Const(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        regex = "( " + self.name + ")"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "[" + self.name + "]"
        else:
            return self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return val[1:]


class Int(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        regex = "( [0-9]+)"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return int(val[1:])


class Any(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        if self.is_optional:
            return "( .+?)?"
        else:
            return "( .+?)"

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return val[1:]


class Regex(CommandParam):
    def __init__(self, name, regex, is_optional=False, num_groups=1):
        super().__init__()
        self.name = name
        self.regex = regex
        self.is_optional = is_optional
        self.num_groups = num_groups

    def get_regex(self):
        return self.regex

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name

    def process_matches(self, params):
        p = []
        for i in range(self.num_groups):
            p.append(params.pop(0))
        return p


class Options(CommandParam):
    def __init__(self, options, is_optional=False):
        super().__init__()
        self.options = options
        self.is_optional = is_optional

    def get_regex(self):
        regex = "(" + "|".join(map(lambda x: " " + re.escape(x), self.options)) + ")"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "[" + "|".join(self.options) + "]"
        else:
            return "|".join(self.options)

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return val[1:]


class Time(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        regex = "( (([0-9]+)([a-z]+))+)"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name

    def process_matches(self, params):
        budatime_str = params.pop(0)
        params.pop(0)
        params.pop(0)
        params.pop(0)

        if budatime_str is None:
            return None
        else:
            util = Registry.get_instance("util")
            return util.parse_time(budatime_str[1:])


class Item(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        regex = """( <a href="itemref:\/\/(\d+)\/(\d+)\/(\d+)">(.+)<\/a>)"""
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name

    def process_matches(self, params):
        if params.pop(0):
            return MapObject({
                "low_id": int(params.pop(0)),
                "high_id": int(params.pop(0)),
                "ql": int(params.pop(0)),
                "name": params.pop(0)
            })
        else:
            params.pop(0)
            params.pop(0)
            params.pop(0)
            params.pop(0)
            return None
