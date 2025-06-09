import re
from core.registry import Registry
from core.dict_object import DictObject
from core.sender_obj import SenderObj


class CommandParam:
    def get_regex(self):
        pass

    def get_name(self):
        pass

    def process_matches(self, params):
        pass


class Const(CommandParam):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"(\s+" + self.name + ")"
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
            return val.lstrip()


class Int(CommandParam):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"(\s+[0-9]+)"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return int(val.lstrip())


class SignedInt(Int):
    def __init__(self, name, is_optional=False):
        super().__init__(name, is_optional)

    def get_regex(self):
        regex = r"(\s+\-?[0-9]+)"
        return regex + ("?" if self.is_optional else "")


class Decimal(CommandParam):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"(\s+[0-9]*\.?[0-9]+)"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return float(val.lstrip())


class Any(CommandParam):
    def __init__(self, name, is_optional=False, allowed_chars="."):
        self.name = name
        self.is_optional = is_optional
        self.allowed_chars = allowed_chars
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"(\s+%s+?)" % self.allowed_chars
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        val = params.pop(0)
        if val is None:
            return None
        else:
            return val.lstrip()


class Regex(CommandParam):
    def __init__(self, name, regex, is_optional=False, num_groups=1):
        self.name = name
        self.regex = regex
        self.is_optional = is_optional
        self.num_groups = num_groups
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        return self.regex

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        p = []
        for i in range(self.num_groups):
            p.append(params.pop(0))
        return p


class Options(CommandParam):
    def __init__(self, options, is_optional=False):
        self.options = options
        self.is_optional = is_optional
        for name in options:
            if " " in name:
                raise Exception("One or more spaces found in command param option '%s'." % name)

    def get_regex(self):
        regex = r"(" + "|".join(map(lambda x: r"\s+" + re.escape(x), self.options)) + ")"
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
            return val.lstrip()


class Time(CommandParam):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"(\s+(([0-9]+)([a-z]+))+)"
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        budatime_str = params.pop(0)
        params.pop(0)
        params.pop(0)
        params.pop(0)

        if budatime_str is None:
            return None
        else:
            util = Registry.get_instance("util")
            return util.parse_time(budatime_str.lstrip())


class Item(CommandParam):
    def __init__(self, name, is_optional=False):
        self.name = name
        self.is_optional = is_optional
        if " " in name:
            raise Exception("One or more spaces found in command param '%s'." % name)

    def get_regex(self):
        regex = r"""(\s*<a href=["']itemref:\/\/(\d+)\/(\d+)\/(\d+)["']>(.+?)<\/a>)"""
        return regex + ("?" if self.is_optional else "")

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]</highlight>" % self.name
        else:
            return "<highlight>%s</highlight>" % self.name

    def process_matches(self, params):
        if params.pop(0):
            return DictObject({
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


class Character(Any):
    def __init__(self, name, is_optional=False):
        super().__init__(name, is_optional)

    def get_regex(self):
        regex = r"(\s+[\d+a-z-]+)"
        return regex + ("?" if self.is_optional else "")

    def process_matches(self, params):
        val = super().process_matches(params)

        if val is None:
            return None
        else:
            character_service = Registry.get_instance("character_service")
            access_service = Registry.get_instance("access_service")
            char_id = character_service.resolve_char_to_id(val)
            if char_id is None:
                return SenderObj(char_id, val.capitalize(), None)
            else:
                return SenderObj(char_id, val.capitalize(), access_service.get_access_level(char_id))


# Note: NamedParameters should always go at the end of the command parameter list
# Note: NamedParameters need to be validated manually to ensure they have valid values
class NamedParameters(CommandParam):
    def __init__(self, names):
        self.names = names
        for name in names:
            if " " in name:
                raise Exception("One or more spaces found in command named param option '%s'." % name)

    def get_regex(self):
        regex = "((" + "|".join(map(lambda x: r"\s+--%s=.+?" % x, self.names)) + ")*)"
        return regex

    def get_name(self):
        return " ".join(map(lambda x: f"[--{x}=<highlight>{x}</highlight>]", self.names))

    def process_matches(self, params):
        v = params.pop(0)
        params.pop(0)

        regex = "^(" + "|".join(map(lambda x: r"(\s+--(%s)=(.+?))" % x, self.names)) + ")*$"
        p = re.compile(regex)
        results = p.findall(v)[0][1:]
        values = DictObject()
        for name in self.names:
            values[name] = results[2]
            results = results[3:]
        return values


# Note: NamedFlagParameters should always go at the end of the command parameter list
class NamedFlagParameters(CommandParam):
    def __init__(self, names):
        super().__init__()
        self.names = names
        for name in names:
            if " " in name:
                raise Exception("One or more spaces found in command named param option '%s'." % name)

    def get_regex(self):
        regex = "((" + "|".join(map(lambda x: r"\s+--%s" % x, self.names)) + ")*)"
        return regex

    def get_name(self):
        return " ".join(map(lambda x: "[--%s]" % x, self.names))

    def process_matches(self, params):
        v = params.pop(0)
        params.pop(0)

        regex = "^(" + "|".join(map(lambda x: r"(\s+--(%s))" % x, self.names)) + ")*$"
        p = re.compile(regex)
        results = p.findall(v)[0][1:]
        values = DictObject()
        for name in self.names:
            values[name] = True if results[1] else False
            results = results[2:]
        return values


# Note: cannot be used with Any due to eagerness!
class Multiple(CommandParam):
    def __init__(self, inner_type, min_num=1, max_num=None):
        if type(inner_type) is Any:
            # Any type ignores is_optional and allowed_chars params, and can only capture
            # single words (no spaces) when used with Multiple
            def get_regex():
                regex = r"(\s+[^ ]+)"
                return regex

            inner_type.get_regex = get_regex

        self.inner_type = inner_type
        self.min = min_num or ""
        self.max = max_num or ""

    def get_regex(self):
        regex = "(" + self.inner_type.get_regex() + "{%s,%s})" % (self.min, self.max)
        return regex

    def get_name(self):
        return self.inner_type.get_name() + "*"

    def process_matches(self, params):
        v = params.pop(0)

        # remove unused params
        self.inner_type.process_matches(params)

        results = []
        p = re.compile(self.inner_type.get_regex(), re.IGNORECASE | re.DOTALL)

        matches = p.search(v)
        while matches:
            v = v[matches.end():]
            a = self.inner_type.process_matches(list(matches.groups()))
            results.append(a)
            matches = p.search(v)

        return results
