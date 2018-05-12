import re
from core.registry import Registry


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
        return params.pop(0)


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
            return int(val)


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
        return params.pop(0)


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
        self.options = list(map(lambda x: re.escape(x), options))
        self.is_optional = is_optional

    def get_regex(self):
        regex = "(" + "|".join(map(lambda x: " " + x, self.options)) + ")"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "[" + "|".join(self.options) + "]"
        else:
            return "|".join(self.options)

    def process_matches(self, params):
        return params.pop(0)


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
            return util.parse_time(budatime_str)
