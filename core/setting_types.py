from core.registry import Registry
import json
import re


class SettingType:
    def __init__(self):
        self.setting_service = Registry.get_instance("setting_service")
        self.name = None

    def set_name(self, name):
        self.name = name

    def _get_raw_value(self):
        return self.setting_service.get_value(self.name)

    def _set_raw_value(self, value):
        self.setting_service.set_value(self.name, value)

    def set_value(self, value):
        pass

    def get_value(self):
        return self._get_raw_value()

    def get_display_value(self):
        return "<highlight>%s<end>" % self.get_value()

    def set_description(self, description):
        self.description = description

    def get_description(self):
        return self.description


class TextSettingType(SettingType):
    def __init__(self, options=None):
        super().__init__()
        self.options = options

    def set_value(self, value):
        if len(str(value)) > 255:
            raise Exception("Setting value cannot be longer than 255 characters.")
        else:
            self._set_raw_value(value)

    def get_display_value(self):
        return "<highlight>%s<end>" % (self.get_value() or "&lt;empty&gt;")

    def get_display(self):
        text = Registry.get_instance("text")
        options_str = "\n".join(map(lambda opt: text.make_chatcmd(str(opt), "/tell <myname> config setting %s set %s" % (self.name, opt)), self.options))

        return """For this setting you can enter any text you want (max. 255 characters).
To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ set <i>_value_</i><end>

Or choose an option below:\n\n""" + options_str


class DictionarySettingType(SettingType):
    def __init__(self):
        super().__init__()

    def set_value(self, value):
        if not value:
            self._set_raw_value("")
        elif isinstance(value, dict):
            self._set_raw_value(json.dumps(value))
        else:
            raise Exception("Value must be a dictionary.")

    def get_value(self):
        value = self._get_raw_value()
        if value:
            return json.loads(value)
        else:
            return value

    def get_display_value(self):
        return "<highlight>%s<end>" % (self.get_value() or "&lt;empty&gt;")

    def get_display(self):
        return """This setting is control by the bot and cannot be set manually."""


class HiddenSettingType(TextSettingType):
    def __init__(self, options=None):
        super().__init__()
        self.options = options

    def get_display_value(self):
        return "<highlight>%s<end>" % "&lt;hidden&gt;"

    def get_display(self):
        return """For this setting you can enter any text you want (max. 255 characters).
To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ set <i>_value_</i><end>

The saved value is never shown in the config."""


class ColorSettingType(SettingType):
    def __init__(self):
        super().__init__()

    def get_display_value(self):
        return self.get_font_color() + self.get_value() + "<end>"

    def set_value(self, value):
        if re.match("^#([0-9a-fA-F]{6})$", str(value)):
            self._set_raw_value(value.upper())
        else:
            raise Exception("You must enter a valid HTML color.")

    def get_display(self):
        return """For this setting you can set any Color in the HTML Hexadecimal Color Format.
You can change it manually with the command:

/tell <myname> config setting """ + self.name + """ set <i>_HTML Color_</i>

Or you can choose one of the following colors

<font color='#FF0000'>Red</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FF0000'>Save it</a>)
<font color='#FFFFFF'>White</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FFFFFF'>Save it</a>)
<font color='#808080'>Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #808080'>Save it</a>)
<font color='#DDDDDD'>Light Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #DDDDDD'>Save it</a>)
<font color='#9CC6E7'>Dark Grey</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #9CC6E7'>Save it</a>)
<font color='#000000'>Black</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #000000'>Save it</a>)
<font color='#FFFF00'>Yellow</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FFFF00'>Save it</a>)
<font color='#8CB5FF'>Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #8CB5FF'>Save it</a>)
<font color='#00BFFF'>Deep Sky Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #00BFFF'>Save it</a>)
<font color='#00DE42'>Green</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #00DE42'>Save it</a>)
<font color='#FCA712'>Orange</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FCA712'>Save it</a>)
<font color='#FFD700'>Gold</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FFD700'>Save it</a>)
<font color='#FF1493'>Deep Pink</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FF1493'>Save it</a>)
<font color='#EE82EE'>Violet</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #EE82EE'>Save it</a>)
<font color='#8B7355'>Brown</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #8B7355'>Save it</a>)
<font color='#00FFFF'>Cyan</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #00FFFF'>Save it</a>)
<font color='#000080'>Navy Blue</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #000080'>Save it</a>)
<font color='#FF8C00'>Dark Orange</font> (<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set #FF8C00'>Save it</a>)"""

    def get_font_color(self):
        return "<font color='%s'>" % self.get_value()

    def get_int_value(self):
        return int(self.get_value().replace("#", ""), 16)


class NumberSettingType(SettingType):
    def __init__(self, options=None):
        super().__init__()
        self.options = options

    def get_value(self):
        return int(self._get_raw_value())

    def set_value(self, value):
        if re.match("^\d+$", str(value)):
            self._set_raw_value(value)
        else:
            raise Exception("You must enter a positive integer for this setting.")

    def get_display(self):
        text = Registry.get_instance("text")
        options_str = "\n".join(map(lambda opt: text.make_chatcmd(str(opt), "/tell <myname> config setting %s set %s" % (self.name, opt)), self.options))

        return """For this setting you can set any positive integer.
To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ set <i>_number_</i><end>

Or choose an option below:\n\n""" + options_str


class TimeSettingType(SettingType):
    def __init__(self, options=None):
        super().__init__()
        self.options = options

    def get_value(self):
        return int(self._get_raw_value())

    def get_display_value(self):
        util = Registry.get_instance("util")
        return "<highlight>%s<end>" % util.time_to_readable(self.get_value())

    def set_value(self, value):
        util = Registry.get_instance("util")
        time = util.parse_time(value)
        if time > 0:
            self._set_raw_value(time)
        else:
            raise Exception("You must enter time in a valid Budatime format")

    def get_display(self):
        text = Registry.get_instance("text")
        options_str = "\n".join(map(lambda opt: text.make_chatcmd(str(opt), "/tell <myname> config setting %s set %s" % (self.name, opt)), self.options))

        return """For this setting you must enter a time value. See <a href='chatcmd:///tell <myname> help budatime'>budatime</a> for info on the format of the 'time' parameter.

To change this setting:

<highlight>/tell <myname> config setting """ + self.name + """ set <i>_time_</i><end>

Or choose an option below:\n\n""" + options_str


class BooleanSettingType(SettingType):
    def __init__(self):
        super().__init__()

    def get_value(self):
        return int(self._get_raw_value()) == 1

    def get_display_value(self):
        return "<highlight>%s<end>" % ("True" if self.get_value() else "False")

    def set_value(self, value):
        if value.lower() == "true":
            self._set_raw_value(1)
        elif value.lower() == "false":
            self._set_raw_value(0)
        else:
            raise Exception("You must enter either 'true' or 'false'")

    def get_display(self):
        return """For this setting you can enter either true or false.

<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set true'>True</a>
<a href='chatcmd:///tell <myname> config setting """ + self.name + """ set false'>False</a>"""
