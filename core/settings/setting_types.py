class SettingType:
    def get_value(self):
        pass

    def set_value(self, value):
        pass

    def get_display(self):
        pass


class TextSettingType(SettingType):
    def __init__(self, value, options=None):
        self.set_value(value)
        self.options = options

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_display(self):
        return ""


class ColorSettingType(SettingType):
    def __init__(self, value):
        self.set_value(value)

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_display(self):
        return ""

    def get_font_color(self):
        return "<font color='%s'>" % self.value


class NumberSettingType(SettingType):
    def __init__(self, value, options=None):
        self.set_value(value)
        self.options = options

    def get_value(self):
        return int(self.value)

    def set_value(self, value):
        self.value = value

    def get_display(self):
        return ""
