import re


class CommandParam:
    def __init__(self):
        pass


class Const(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        if self.is_optional:
            return "( " + self.name + ")" + "?"
        else:
            return "( " + self.name + ")"

    def get_name(self):
        if self.is_optional:
            return "[" + self.name + "]"
        else:
            return self.name


class Int(CommandParam):
    def __init__(self, name, is_optional=False):
        super().__init__()
        self.name = name
        self.is_optional = is_optional

    def get_regex(self):
        if self.is_optional:
            return "( [0-9]+)?"
        else:
            return "( [0-9]+)"

    def get_name(self):
        if self.is_optional:
            return "<highlight>[%s]<end>" % self.name
        else:
            return "<highlight>%s<end>" % self.name


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


class Regex:
    def __init__(self, name, regex):
        self.name = name
        self.regex = regex

    def get_regex(self):
        return self.regex

    def get_name(self):
        return "<highlight>%s<end>" % self.name


class Options(CommandParam):
    def __init__(self, options, is_optional=False):
        super().__init__()
        self.options = list(map(lambda x: re.escape(x), options))
        self.is_optional = is_optional

    def get_regex(self):
        if self.is_optional:
            return "( " + "|".join(self.options) + ")?"
        else:
            return "( " + "|".join(self.options) + ")"

    def get_name(self):
        if self.is_optional:
            return "[" + "|".join(self.options) + "]"
        else:
            return "|".join(self.options)
