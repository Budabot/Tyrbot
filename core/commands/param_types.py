import re


class Const:
    def __init__(self, name):
        self.name = name

    def get_regex(self):
        return self.name

    def get_name(self):
        return self.name


class Int:
    def __init__(self, name):
        self.name = name

    def get_regex(self):
        return "([0-9]+)"

    def get_name(self):
        return "<highlight>'%s'<end>" % self.name


class Any:
    def __init__(self, name):
        self.name = name

    def get_regex(self):
        return "(.+?)"

    def get_name(self):
        return "<highlight>'%s'<end>" % self.name


class Regex:
    def __init__(self, name, regex):
        self.name = name
        self.regex = regex

    def get_regex(self):
        return self.regex

    def get_name(self):
        return "<highlight>'%s'<end>" % self.name


class Options:
    def __init__(self, options):
        self.options = list(map(lambda x: re.escape(x), options))

    def get_regex(self):
        return "(" + "|".join(self.options) + ")"

    def get_name(self):
        return "|".join(self.options)
